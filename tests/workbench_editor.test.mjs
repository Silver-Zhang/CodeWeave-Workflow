import {test} from 'node:test';
import assert from 'node:assert/strict';
import {selectedFragment, pasteFragment, removeSelection, arrangeSelection, validConnection,
  inspectorPlacement} from '../tools/studio/workbench_ui/canvas_editing.mjs';

const graph = () => ({version: 3, nodes: [
  {id: 'start', kind: 'start', position: {x: 0, y: 0}},
  {id: 'a', kind: 'agent', name: 'A', session: 'private-native', position: {x: 50, y: 20}},
  {id: 'b', kind: 'agent', name: 'B', session: 'native-B', position: {x: 400, y: 100}},
  {id: 'c', kind: 'result', name: 'C', position: {x: 900, y: 250}}],
edges: [{id: 'in', source: 'start', target: 'a'}, {id: 'ab', source: 'a', target: 'b', label: '公开回答'},
        {id: 'out', source: 'b', target: 'c'}]});

test('copy connected selection preserves topology, keeps one input and never duplicates a native writer', () => {
  const g = graph(), original = structuredClone(g), fragment = selectedFragment(g, ['start', 'a', 'b']);
  let i = 0; const result = pasteFragment(g, fragment, prefix => prefix + (++i));
  assert.equal(result.graph.nodes.filter(n => n.kind === 'start').length, 1);
  assert.equal(result.selected.length, 2);
  const copied = result.graph.nodes.filter(n => result.selected.includes(n.id));
  assert.deepEqual(copied.map(n => n.session), ['new', 'new']);
  assert.deepEqual(copied[0].position, {x: 90, y: 60});
  assert.equal(result.graph.edges.at(-1).source, copied[0].id);
  assert.equal(result.graph.edges.at(-1).target, copied[1].id);
  assert.equal(result.graph.edges.at(-1).label, '公开回答');
  assert.deepEqual(g, original);
});

test('delete removes only selected nodes and dangling edges without changing the source document', () => {
  const g = graph(), removed = removeSelection(g, ['b']);
  assert.deepEqual(removed.edges.map(e => e.id), ['in']);
  assert.equal(g.edges.length, 3);
});

test('distribution uses actual node widths and gives equal gaps', () => {
  const g = graph(), sizes = {a: {width: 100}, b: {width: 200}, c: {width: 300}};
  const result = arrangeSelection(g, ['a', 'b', 'c'], 'horizontal', sizes);
  const [a, b, c] = result.nodes.slice(1);
  assert.equal(b.position.x - a.position.x - 100, c.position.x - b.position.x - 200);
  assert.equal(c.position.x, 900);
});

test('right alignment uses live dimensions and leaves unselected nodes alone', () => {
  const result = arrangeSelection(graph(), ['a', 'b'], 'right', {a: {width: 100}, b: {width: 200}});
  assert.equal(result.nodes[1].position.x + 100, result.nodes[2].position.x + 200);
  assert.equal(result.nodes[3].position.x, 900);
});

test('connections reject cycles, duplicate edges and invalid input/output direction', () => {
  const g = graph();
  assert.equal(validConnection(g, 'b', 'a'), false);
  assert.equal(validConnection(g, 'a', 'b'), false);
  assert.equal(validConnection(g, 'c', 'a'), false);
  assert.equal(validConnection(g, 'b', 'start'), false);
  assert.equal(validConnection(g, 'a', 'b', 'ab'), true);
});

test('inspector uses a free side or reserves sidebar instead of covering its target', () => {
  const bounds = {left: 200, right: 1200, top: 100, bottom: 800};
  assert.equal(inspectorPlacement({left: 300, right: 500, top: 200}, bounds).x, 516);
  assert.equal(inspectorPlacement({left: 900, right: 1100, top: 200}, bounds).x, 514);
  assert.equal(inspectorPlacement({left: 450, right: 850, top: 200}, bounds).pinned, true);
});
