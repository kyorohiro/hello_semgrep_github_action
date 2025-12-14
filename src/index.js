import http from "node:http";

const port = process.env.PORT ? Number(process.env.PORT) : 3000;

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader("content-type", "text/plain; charset=utf-8");
  res.end("Hello World\n");
});

server.listen(port, () => {
  console.log(`listening on http://localhost:${port}`);
});

