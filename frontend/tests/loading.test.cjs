const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
const {Subject} = require('rxjs');
const source = path.resolve(__dirname, '../src/app/loading-state.ts');
const compiled = new Module(source, module);
compiled.paths = module.paths;
compiled._compile(ts.transpileModule(fs.readFileSync(source, 'utf8'), {
  compilerOptions:{module:ts.ModuleKind.CommonJS, target:ts.ScriptTarget.ES2022},
}).outputText, source);
const {LoadingTracker, trackActivity} = compiled.exports;

function fixture() {
  let time = 0, id = 0, state;
  const timers = new Map();
  const clock = {
    now:()=>time,
    set:(callback, delay)=>{timers.set(++id, {callback, at:time + delay}); return id;},
    clear:handle=>timers.delete(handle),
  };
  const tracker = new LoadingTracker((pending, visible)=>{state = {pending, visible};}, clock);
  return {tracker, state:()=>state, timers, advance(delta) {
    const until = time + delta;
    while (true) {
      const next = [...timers].sort((a,b)=>a[1].at-b[1].at)[0];
      if (!next || next[1].at > until) break;
      time = next[1].at; timers.delete(next[0]); next[1].callback();
    }
    time = until;
  }};
}

test('quick operations do not flash the indicator', () => {
  const f = fixture(), end = f.tracker.begin();
  f.advance(100); end(); f.advance(1000);
  assert.deepEqual(f.state(), {pending:false, visible:false});
  assert.equal(f.timers.size, 0);
});

test('concurrent operations keep loading until the last finishes', () => {
  const f = fixture(), endA = f.tracker.begin(), endB = f.tracker.begin();
  f.advance(180);
  assert.deepEqual(f.state(), {pending:true, visible:true});
  endA(); endA(); f.advance(500);
  assert.deepEqual(f.state(), {pending:true, visible:true});
  endB(); f.advance(0);
  assert.deepEqual(f.state(), {pending:false, visible:false});
});

test('minimum visibility and a new operation prevent flicker between requests', () => {
  const f = fixture(), endA = f.tracker.begin();
  f.advance(180); endA(); f.advance(100);
  assert.deepEqual(f.state(), {pending:false, visible:true});
  const endB = f.tracker.begin(); f.advance(120);
  assert.deepEqual(f.state(), {pending:true, visible:true});
  endB(); f.advance(0);
  assert.deepEqual(f.state(), {pending:false, visible:false});
});

test('errors, including synchronous errors, release the loading counter', () => {
  const f = fixture(), source = new Subject();
  const request = trackActivity(()=>f.tracker.begin(), ()=>source);
  request.subscribe({error:()=>{}});
  f.advance(500); source.error(new Error('Network error')); f.advance(0);
  assert.deepEqual(f.state(), {pending:false, visible:false});
  trackActivity(()=>f.tracker.begin(), ()=>{throw new Error('Synchronous error');})
    .subscribe({error:()=>{}});
  f.advance(500);
  assert.deepEqual(f.state(), {pending:false, visible:false});
});

test('each subscription starts independently and cancellation releases its activity', () => {
  const f = fixture(), source = new Subject();
  const request = trackActivity(()=>f.tracker.begin(), ()=>source);
  assert.equal(f.state(), undefined);
  const a = request.subscribe(), b = request.subscribe();
  f.advance(500); a.unsubscribe();
  assert.deepEqual(f.state(), {pending:true, visible:true});
  b.unsubscribe(); f.advance(0);
  assert.deepEqual(f.state(), {pending:false, visible:false});
});

test('destroying the tracker cancels pending timers and ignores late completion', () => {
  const f = fixture(), end = f.tracker.begin();
  f.tracker.dispose(); end(); f.tracker.begin()(); f.advance(1000);
  assert.deepEqual(f.state(), {pending:false, visible:false});
  assert.equal(f.timers.size, 0);
});
