const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const context={window:{},Intl};
vm.runInNewContext(readFileSync(path.join(__dirname,'../static/js/room-model.js'),'utf8'),context);
const model=context.window.RoomModel;
const room={id:'r2',kind:'dormitory',name:'Kí túc xá',devices:[
  {id:'light1',kind:'light',name:'Đèn <script>alert(1)</script>',current_a:.043,is_on:false},
  {id:'light2',kind:'light',name:'Đèn 02',current_a:.043,is_on:true},
]};

test('detail uses native controls and short codes while preserving accessible full names',()=>{
  const html=model.render(room,true);
  assert.equal((html.match(/<button /g)||[]).length,2);
  assert.equal((html.match(/data-model-device=/g)||[]).length,2);
  assert.ok(html.includes('aria-pressed="true"'));
  assert.ok(html.includes('Đèn &lt;script&gt;'));
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('>Đ1</span>'));
  assert.ok(html.includes('>Đ2</span>'));
});

test('Home shares detail positions and never introduces interactive device controls',()=>{
  const preview=model.render(room);
  const detail=model.render(room,true);
  assert.ok(!preview.includes('<button'));
  const coordinates=html=>[...html.matchAll(/style="left:([^;]+);top:([^"]+)"/g)].map(match=>match[0]);
  assert.deepEqual(coordinates(preview),coordinates(detail));
  assert.deepEqual(room.devices.map(item=>item.is_on),[false,true]);
});

test('state updates retain complete names and disable pending or unavailable controls',()=>{
  const nodes=new Map(room.devices.map(item=>[item.id,{tagName:'BUTTON',attrs:{},on:false,
    classList:{toggle(name,value){this.owner.on=value;}},
    setAttribute(name,value){this.attrs[name]=value;}}]));
  for(const node of nodes.values()) node.classList.owner=node;
  const container={querySelector:selector=>nodes.get(selector.match(/"([^"]+)"/)[1])};
  model.update(container,room,false,new Set(['light1']));
  assert.equal(nodes.get('light1').disabled,true);
  assert.equal(nodes.get('light2').disabled,false);
  assert.equal(nodes.get('light2').attrs['aria-pressed'],'true');
  assert.ok(nodes.get('light1').attrs.title.includes('<script>'));
  model.update(container,room,true);
  assert.ok([...nodes.values()].every(node=>node.disabled));
});
