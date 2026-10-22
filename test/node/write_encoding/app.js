require('http').createServer(function (req, res) {
    var encoding = req.url.slice(1);
    var body = encoding == 'hex' ? '414243' : 'café';

    res.writeHead(200, {
        'Content-Type': 'text/plain',
        'Content-Length': Buffer.byteLength(body, encoding)
    }).end(body, encoding);
}).listen(8080);
