const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
const source = path.resolve(__dirname, '../src/app/validation.ts');
const compiled = new Module(source, module);
compiled._compile(ts.transpileModule(fs.readFileSync(source, 'utf8'), {
  compilerOptions:{module:ts.ModuleKind.CommonJS, target:ts.ScriptTarget.ES2022},
}).outputText, source);
const {textError, passwordError, filenameError, modelIdentity, csvError} = compiled.exports;

test('Unicode limits match Python and reject broken text', () => {
  assert.equal(textError('😀'.repeat(80), 'Name', 80), '');
  assert.ok(textError('😀'.repeat(81), 'Name', 80));
  for (const value of ['\ud800', '\udc00', '\0', null, 3]) assert.ok(textError(value, 'Name', 80));
  assert.ok(textError('   ', 'Name', 80));
  assert.equal(textError('   ', 'Reference', 6000, false), '');
});
test('registration and login have different password requirements', () => {
  assert.equal(passwordError('test', false), '');
  assert.ok(passwordError('test', true));
  assert.ok(passwordError(' '.repeat(12), true));
  assert.equal(passwordError(' strong password ', true), '');
  assert.ok(passwordError('x'.repeat(129), false));
});
test('filenames and model aliases are checked consistently', () => {
  for (const name of ['../file.txt', 'a\\b.txt', 'a\n.txt', 'x'.repeat(181)]) assert.ok(filenameError(name));
  assert.equal(filenameError('datos.csv'), '');
  assert.equal(modelIdentity('demo'), modelIdentity('demo:latest'));
  assert.notEqual(modelIdentity('demo'), modelIdentity('demo:small'));
});
test('CSV supports escaped quotes and multiline cells, but rejects broken quoting', () => {
  assert.equal(csvError('name,value\n"a,b","line 1\nline ""2"""'), '');
  assert.equal(csvError('a,b\r\n1,2'), '');
  assert.ok(csvError('a,"unfinished'));
  assert.ok(csvError('"a"garbage,b'));
});
