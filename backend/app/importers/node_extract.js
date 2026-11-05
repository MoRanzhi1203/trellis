const fs = require('fs');

const mode = process.argv[2];
const target = process.argv[3];

if (mode === 'words') {
  global.window = {};
  require(target);
  process.stdout.write(JSON.stringify(global.window.TRELLIS));
} else if (mode === 'legacy-graph') {
  const html = fs.readFileSync(target, 'utf8');
  function grab(name) {
    const re = new RegExp('const ' + name + '\\s*=\\s*(\\[[\\s\\S]*?\\]);');
    const match = html.match(re);
    if (!match) throw new Error('missing ' + name);
    return match[1];
  }
  const nodes = eval(grab('NODES'));
  const edges = eval(grab('EDGES'));
  process.stdout.write(JSON.stringify({ nodes, edges }));
} else {
  throw new Error('unknown mode: ' + mode);
}
