"""unitd started with "--config FILE", "--control none" and "--pid none".

The configuration comes from FILE, so a container can start unitd without a
control socket, a pid file or a writable state directory; a FILE that cannot
run stops unitd with exit status 1 instead of starting it empty.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from unit.http import HTTP1
from unit.option import option
from unit.utils import public_dir, waitforfiles

client = HTTP1()


class Unitd:
    """A unitd of our own: the shared one runs with the default options."""

    def __init__(self):
        self.unitd = f'{option.current_dir}/build/sbin/unitd'

        if not Path(self.unitd).is_file():
            pytest.skip('could not find unitd')

        self.dir = tempfile.mkdtemp(prefix='unit-test-config-')
        public_dir(self.dir)

        self.log = f'{self.dir}/unit.log'
        self.listener = f'{self.dir}/app.sock'
        self.control = f'{self.dir}/control.unit.sock'
        self.state = f'{self.dir}/state'
        self.config = f'{self.dir}/config.json'
        self.stderr = f'{self.dir}/stderr.log'
        self.process = None

    def returning(self, status):
        """A configuration that answers every request with status."""
        return {
            "listeners": {f"unix:{self.listener}": {"pass": "routes"}},
            "routes": [{"action": {"return": status}}],
        }

    def start(self, conf, control=True):
        if conf is not None:
            text = conf if isinstance(conf, str) else json.dumps(conf)
            Path(self.config).write_text(text, encoding='utf-8')

        env = os.environ.copy()

        # As in conftest.unit_run(): PYTHONHOME must not be set for pytest.
        pythonhome = env.pop('UNIT_PYTHONHOME', None)
        if pythonhome:
            env['PYTHONHOME'] = pythonhome

        builddir = f'{option.current_dir}/build'

        # A file that cannot be read or is not JSON is reported before
        # unitd opens its log, so on stderr.
        stderr = open(self.stderr, 'w', encoding='utf-8')

        self.process = subprocess.Popen(
            [
                self.unitd,
                '--no-daemon',
                '--modulesdir',
                f'{builddir}/lib/unit/modules',
                '--statedir',
                self.state,
                '--pid',
                'none',
                '--log',
                self.log,
                '--control',
                f'unix:{self.control}' if control else 'none',
                '--tmpdir',
                self.dir,
                '--config',
                self.config,
            ],
            stdout=subprocess.DEVNULL,
            stderr=stderr,
            start_new_session=True,
            env=env,
        )

        stderr.close()

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGQUIT)

            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=30)

        shutil.rmtree(self.dir, ignore_errors=True)

    def read_log(self):
        """unit.log and the stderr written before it existed."""
        text = ''

        for path in (self.stderr, self.log):
            if Path(path).exists():
                text += Path(path).read_text(encoding='utf-8', errors='replace')

        return text

    def get(self, url='/', addr=None):
        return client.get(
            url=url, sock_type='unix', addr=addr or self.listener
        )


@pytest.fixture
def unitd():
    instance = Unitd()

    yield instance

    instance.stop()


def default_paths(unitd):
    """The built-in pid file and control socket paths, from "--help"."""
    text = subprocess.run(
        [unitd.unitd, '--help'], capture_output=True, text=True, check=True
    ).stdout

    paths = []

    for option_name in ('--control', '--pid'):
        found = re.search(
            rf'^  {option_name} .*?default: "([^"]+)"', text, re.M | re.S
        )
        assert found, f'{option_name} default in --help'
        paths.append(Path(found.group(1).removeprefix('unix:')))

    return paths


def test_config_file_no_control_no_pid_no_state(unitd):
    defaults = {path: path.exists() for path in default_paths(unitd)}

    unitd.start(unitd.returning(204), control=False)

    assert waitforfiles(unitd.listener), f'listener\n{unitd.read_log()}'
    assert unitd.get()['status'] == 204, 'configuration from the file'

    assert unitd.process.poll() is None, 'running'
    assert not Path(unitd.state).exists(), 'state directory not created'
    assert sorted(p.name for p in Path(unitd.dir).iterdir()) == [
        'app.sock',
        'config.json',
        'stderr.log',
        'unit.log',
    ], 'no pid file and no control socket'

    # "none" must not fall back to the built-in paths either.
    for path, existed in defaults.items():
        assert path.exists() == existed, f'{path} untouched'


def test_config_file_utf8_bom(unitd):
    Path(unitd.config).write_bytes(
        b'\xef\xbb\xbf' + json.dumps(unitd.returning(204)).encode()
    )

    unitd.start(None)

    assert waitforfiles(unitd.listener), f'listener\n{unitd.read_log()}'
    assert unitd.get()['status'] == 204, 'a BOM is skipped as by the API'


def test_config_file_ignores_state(unitd):
    Path(unitd.state).mkdir()
    Path(f'{unitd.state}/conf.json').write_text(
        json.dumps(unitd.returning(418)), encoding='utf-8'
    )

    unitd.start(unitd.returning(204))

    assert waitforfiles(unitd.listener), f'listener\n{unitd.read_log()}'
    assert unitd.get()['status'] == 204, 'the file wins over conf.json'


def test_config_file_read_only_api(unitd):
    conf = unitd.returning(204)

    unitd.start(conf)

    assert waitforfiles(unitd.listener, unitd.control), unitd.read_log()

    resp = unitd.get('/config', addr=unitd.control)
    assert resp['status'] == 200, 'GET /config'
    assert json.loads(resp['body']) == conf, 'GET returns the file'

    assert unitd.get('/status', addr=unitd.control)['status'] == 200, 'status'

    for method in ('PUT', 'POST', 'DELETE'):
        resp = client.http(
            method,
            url='/config/routes',
            body='[]',
            sock_type='unix',
            addr=unitd.control,
        )
        assert resp['status'] == 405, method
        assert 'read-only' in resp['body'], f'{method} body'

    assert unitd.get()['status'] == 204, 'configuration unchanged'


def controller_pid(main_pid):
    """The pid of the controller child of main, or None."""
    children = Path(f'/proc/{main_pid}/task/{main_pid}/children').read_text()

    for pid in children.split():
        cmdline = Path(f'/proc/{pid}/cmdline').read_bytes()
        if b'controller' in cmdline:
            return int(pid)

    return None


def wait_for(predicate, what, unitd):
    """Polls predicate for up to 10 s and returns its first true value."""
    for _ in range(100):
        value = predicate()
        if value:
            return value
        time.sleep(0.1)

    pytest.fail(f'{what}\n{unitd.read_log()}')


def control_get(unitd):
    """GET /config, or None while no controller answers."""
    try:
        resp = unitd.get('/config', addr=unitd.control)
    except OSError:
        return None

    return resp if resp['status'] == 200 else None


def test_config_file_controller_restart_keeps_config(unitd):
    conf = unitd.returning(204)

    unitd.start(conf)

    assert waitforfiles(unitd.listener, unitd.control), unitd.read_log()

    old = controller_pid(unitd.process.pid)
    assert old is not None, 'controller'

    # A broken file must not reach the restarted controller.
    Path(unitd.config).write_text('{"listeners": ', encoding='utf-8')
    os.kill(old, signal.SIGKILL)

    wait_for(
        lambda: controller_pid(unitd.process.pid) not in (None, old),
        'controller not restarted',
        unitd,
    )

    assert unitd.process.poll() is None, 'unitd keeps running'

    resp = wait_for(lambda: control_get(unitd), 'no GET /config', unitd)

    assert json.loads(resp['body']) == conf, 'the checked configuration'
    assert unitd.get()['status'] == 204, 'still served'


def invalid_cases():
    """(conf, alert, modules); {config} and {dir} are filled in per test."""
    return [
        pytest.param(
            None,
            r'cannot read the configuration file "{config}"',
            {},
            id='missing',
        ),
        pytest.param(
            '{"listeners": ',
            r'the configuration file "{config}" is not valid JSON at '
            r'line 1, column \d+',
            {},
            id='json',
        ),
        pytest.param(
            {"listeners": {"*:7999": {"pass": "routes/missing"}}},
            r'the configuration file "{config}" is invalid at '
            r'"/listeners/\*:7999/pass"',
            {},
            id='invalid',
        ),
        pytest.param(
            {
                "listeners": {
                    "*:7999": {
                        "pass": "routes",
                        "tls": {"certificate": "missing"},
                    }
                },
                "routes": [],
            },
            r'the configuration file "{config}" is invalid at '
            r'"/listeners/\*:7999/tls/certificate": '
            r'Certificate "missing" is not found',
            {'openssl': 'any'},
            id='certificate',
        ),
        pytest.param(
            {
                "listeners": {"unix:{dir}/missing/x.sock": {"pass": "routes"}},
                "routes": [{"action": {"return": 204}}],
            },
            r'failed to apply the configuration file "{config}"',
            {},
            id='apply',
        ),
    ]


@pytest.mark.parametrize('conf, alert, modules', invalid_cases())
def test_config_file_invalid_exits(unitd, require, conf, alert, modules):
    if modules:
        require({'modules': modules})

    if isinstance(conf, dict):
        conf = json.loads(json.dumps(conf).replace('{dir}', unitd.dir))

    unitd.start(conf)

    assert unitd.process.wait(timeout=30) == 1, 'exit status'

    alert = alert.replace('{config}', re.escape(unitd.config))

    assert re.search(rf'\[alert\].+{alert}', unitd.read_log()), (
        unitd.read_log()
    )
