const fs = require('node:fs');

const ts = require('../node_modules/typescript');
for (const ext of ['.ts','.tsx']) require.extensions[ext] = (module, filename) => module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,filename);
const assert = require('node:assert/strict');
const {test} = require('node:test');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {streamEvents} = require('../src/api/stream.ts');
const {parseHistory} = require('../src/hooks/useQueryHistory.ts');
const Answer = require('../src/components/analysis/FinalAnswerCard.tsx').default;
const originalFetch = global.fetch;
function stream(chunks) {const encoder=new TextEncoder();global.fetch=async()=>new Response(new ReadableStream({start(controller){for(const chunk of chunks)controller.enqueue(encoder.encode(chunk));controller.close();}}));}
test('SSE handles split CRLF records, multiline data and trailing terminal event',async()=>{try{stream(['data: {"type":"tool_','done",\r\ndata: "step_index":2}\r\n\r','\ndata: {"type":"completed"}']);const events=[];await streamEvents('/local',{},e=>events.push(e));assert.deepEqual(events.map(e=>e.type),['tool_done','completed']);assert.equal(events[0].step_index,2);}finally{global.fetch=originalFetch;}});
test('SSE rejects truncated and malformed responses',async()=>{try{stream(['data: {"type":"tool_done"}\n\n']);await assert.rejects(streamEvents('/local',{},()=>{}),/before a result/);stream(['data: nope\n\n']);await assert.rejects(streamEvents('/local',{},()=>{}));}finally{global.fetch=originalFetch;}});
test('SSE suppresses callbacks after cancellation',async()=>{try{stream(['data: {"type":"tool_done"}\n\ndata: {"type":"completed"}\n\n']);const controller=new AbortController();let calls=0;await streamEvents('/local',{},()=>{calls++;controller.abort();},controller.signal);assert.equal(calls,1);}finally{global.fetch=originalFetch;}});
test('history rejects malformed storage and unsafe optional display values',()=>{assert.deepEqual(parseHistory('{'),[]);assert.deepEqual(parseHistory('{}'),[]);const entry={id:'x',query:'q',scenarioId:null,confidence:0,confidenceLevel:'low',finalAnswer:'a',timestamp:1};assert.equal(parseHistory(JSON.stringify([entry])).length,1);assert.equal(parseHistory(JSON.stringify([{...entry,aoiName:{bad:true}}])).length,0);assert.equal(parseHistory(JSON.stringify([{...entry,outcome:'invented'}])).length,0);assert.equal(parseHistory(JSON.stringify(Array(20).fill(entry))).length,10);});
for(const [outcome,label] of Object.entries({completed_supported:'Supported computation',completed_partial:'Partial result',abstained:'Abstained',unsupported:'Unsupported request',failed:'Analysis failed'}))test(`renders ${outcome} with limitations and unverified status`,()=>{const html=renderToStaticMarkup(React.createElement(Answer,{query:'test',answer:'Actual computation',confidence:0,confidenceLevel:'low',evidenceStatus:'insufficient',evidencePoints:[],outcome,limitations:['Fixture limitation'],verified:false,scoreKind:'heuristic_evidence'}));assert.ok(html.includes(label));assert.ok(html.includes('Fixture limitation'));assert.ok(html.includes('Not independently verified'));assert.ok(html.includes('not a calibrated probability'));});
