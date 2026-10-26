const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert.equal(html, fs.readFileSync(path.join(root, 'static/index.html'), 'utf8'));
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function start(stored = '[]', blocked = false) {
  const nodes = new Map();
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, { value: '', textContent: '', innerHTML: '', handlers: {},
      addEventListener(type, handler) { this.handlers[type] = handler; } });
    return nodes.get(id);
  };
  const storage = { value: stored };
  const context = vm.createContext({ document: { getElementById: node }, localStorage: {
    getItem() { if (blocked) throw Error('Blocked'); return storage.value; },
    setItem(key, value) { if (blocked) throw Error('Blocked'); storage.value = value; }
  }});
  vm.runInContext(script, context);
  const run = code => vm.runInContext(code, context);
  const submit = (service, message, severity = 'auto') => {
    node('service').value = service; node('message').value = message; node('severity').value = severity;
    node('form').handlers.submit({ preventDefault() {} });
  };
  return { node, run, submit, storage };
}

const app = start();
app.node('demo').handlers.click();
assert.equal(app.node('events').textContent, 6);
assert.equal(app.node('active').textContent, 5);
assert.equal(app.node('dupes').textContent, 1);
assert.equal(app.node('critical').textContent, 1);
app.node('list').handlers.change({ target: {
  matches: () => true, dataset: { id: '1' }, value: 'investigating'
}});
app.submit('CHECKOUT-API', 'Database timeout after 9999ms');
assert.equal(app.run('items[0].occurrences'), 3);
assert.equal(app.run('items[0].status'), 'investigating');
app.node('list').handlers.change({ target: {
  matches: () => true, dataset: { id: '1' }, value: 'resolved'
}});
app.submit('checkout-api', 'Database timeout after 4000ms', 'critical');
assert.equal(app.run('items[0].status'), 'open');
assert.equal(app.run('items[0].severity'), 'critical');
assert.equal(start(app.storage.value).node('events').textContent, 8);
app.submit('test-service', '<img src=x onerror=alert(1)>');
assert.ok(app.node('list').innerHTML.includes('&lt;img'));
assert.ok(!app.node('list').innerHTML.includes('<img'));

for (const data of ['broken json', '{}', '[null,{}, {"id":"bad"}]']) {
  const recovery = start(data);
  assert.equal(recovery.node('events').textContent, 0);
  assert.match(recovery.node('feedback').textContent, /could not be loaded/);
  recovery.submit('checkout-api', 'Database timeout');
  assert.equal(recovery.node('events').textContent, 1);
}
const mixed = start(JSON.stringify([null, ...JSON.parse(app.storage.value)]));
assert.equal(mixed.node('events').textContent, 9);
const temporary = start('[]', true);
temporary.submit('auth-service', 'Unauthorized access detected');
assert.equal(temporary.node('critical').textContent, 1);
assert.match(temporary.node('feedback').textContent, /only kept in this tab/);
console.log('Dashboard checks passed: alerts, grouping, severity, status, reload, escaping and storage recovery.');
