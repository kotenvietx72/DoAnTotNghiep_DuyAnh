// Chạy controller thật với DOM/socket/HTTP tối thiểu; không điều khiển trình duyệt.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');

const source = readFileSync(join(__dirname,'../static/js/app.js'),'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));
const snapshot = (revision=1, mode='devices', warn=12) => ({
  server_id:'test-server',revision,mode,is_simulating:false,
  rooms:Object.fromEntries(['r1','r2','r3'].map(id => [id,{
    id,name:id,current:0,voltage:220,active_count:0,status:'Safe',advice:'',
    thresh_warn:warn,thresh_danger:20,devices:[{id:'light',name:'Đèn',current_a:.1,is_on:false}],
  }])),
});

function harness(page='settings') {
  const ids = ['todayDate','connectionStatus','toastRegion'];
  if (page === 'settings') ids.push('settingsForm','settingsRooms','settingsMessage','saveSettings',
    'resetSettings','confirmReset','cancelReset','resetSettingsDialog');
  else ids.push('roomCurrent','roomVoltage','roomActive','roomTotal','roomStatus','roomLoadText',
    'roomLoadBar','roomWarnThreshold','roomDangerThreshold','roomAdvice','roomModel','deviceList',
    'allDevicesOn','row-light','info-light','switch-light');
  const elements = new Map();
  const element = id => ({
    id,handlers:{},disabled:false,textContent:'',innerHTML:'',children:[{}],style:{},attrs:{},
    classList:{toggle(){}},
    addEventListener(name, fn){this.handlers[name]=fn;},
    setAttribute(name,value){this.attrs[name]=value;},
    append(){},remove(){},
    showModal(){this.open=true;},close(){this.open=false;},
    querySelector(){return elements.get('switch-light');},
  });
  ids.forEach(id => elements.set(id,element(id)));
  const inputs = [{disabled:false}];
  if (page === 'settings') elements.get('settingsForm').reportValidity=()=>true;
  const socket = {};
  const calls = [];
  let state = snapshot();
  let mutation;
  const context = {
    AbortController,Intl,Date,console,
    document:{
      body:{dataset:{page,room:page === 'settings' ? undefined : 'r1'}},
      documentElement:{},
      getElementById:id=>elements.get(id) || null,
      createElement:()=>element('toast'),
      querySelectorAll:selector=>selector.includes('#settingsForm input') ?
        [...['saveSettings','resetSettings','confirmReset'].map(id=>elements.get(id)),...inputs] : [],
    },
    getComputedStyle:()=>({getPropertyValue:()=>''}),
    setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,
    fetch:async (url, options)=>{
      calls.push({url,options});
      if (url === '/api/state') return {ok:true,json:async()=>structuredClone(state)};
      return new Promise((resolve,reject)=>{mutation={resolve,reject};});
    },
    window:{RoomModel:{escape:value=>value,update:(model,room,disabled)=>{model.disabled=disabled;}},
      io:()=>({on:(name,fn)=>{socket[name]=fn;}})},
  };
  context.io=context.window.io;
  context.RoomModel=context.window.RoomModel;
  vm.runInNewContext(source,context,{filename:'app.js'});
  return {
    elements,inputs,calls,socket,
    click:id=>elements.get(id).handlers.click(),
    update:next=>{state=next;socket.state_update(structuredClone(next));},
    succeed:next=>{state=next;mutation.resolve({ok:true,json:async()=>structuredClone(next)});},
    fail:()=>mutation.reject(new Error('connection lost')),
    reject:()=>mutation.resolve({ok:false,json:async()=>({error:'Lưu thất bại'})}),
    setServer:next=>{state=next;},
  };
}

test('reset requires confirmation; cancel preserves draft; success replaces form',async()=>{
  const ui=harness();await flush();
  const form=ui.elements.get('settingsRooms');
  const initial=form.innerHTML;
  ui.elements.get('settingsForm').handlers.input();
  ui.click('resetSettings');
  assert.equal(ui.elements.get('resetSettingsDialog').open,true);
  assert.equal(ui.calls.length,1);
  ui.click('cancelReset');
  assert.equal(form.innerHTML,initial);
  ui.click('resetSettings');ui.click('confirmReset');
  assert.equal(ui.calls.at(-1).url,'/api/settings/reset');
  assert.equal(ui.elements.get('saveSettings').disabled,true);
  assert.equal(ui.inputs[0].disabled,true);
  ui.succeed(snapshot(2,'devices',10));await flush();
  assert.match(form.innerHTML,/value="10"/);
  assert.equal(ui.elements.get('saveSettings').disabled,false);
  assert.match(ui.elements.get('settingsMessage').textContent,/Đã khôi phục/);
});

test('Socket updates preserve unsaved form; clean form follows configuration',async()=>{
  const ui=harness();await flush();
  const form=ui.elements.get('settingsRooms');
  ui.update(snapshot(2,'devices',9));
  assert.match(form.innerHTML,/value="9"/);
  ui.elements.get('settingsForm').handlers.input();
  const draft=form.innerHTML;
  ui.update(snapshot(3,'devices',7));
  assert.equal(form.innerHTML,draft);
  assert.match(ui.elements.get('settingsMessage').textContent,/Bản nháp/);
  ui.update(snapshot(2,'devices',6));
  assert.equal(form.innerHTML,draft);
});

test('lost reset response resynchronizes server state and keeps draft',async()=>{
  const ui=harness();await flush();
  const form=ui.elements.get('settingsRooms');
  const draft=form.innerHTML;
  ui.click('resetSettings');ui.click('confirmReset');
  ui.setServer(snapshot(3,'devices',8));
  ui.fail();await flush();
  assert.equal(ui.calls.at(-1).url,'/api/state');
  assert.equal(form.innerHTML,draft);
  assert.match(ui.elements.get('settingsMessage').textContent,/chưa xác định/);
  assert.equal(ui.elements.get('resetSettings').disabled,false);
});

test('bulk command is single, locks room, then reflects confirmed device state',async()=>{
  const ui=harness('r1');await flush();
  const first=ui.click('allDevicesOn');
  assert.equal(ui.elements.get('allDevicesOn').disabled,true);
  assert.equal(ui.elements.get('switch-light').disabled,true);
  assert.equal(ui.elements.get('roomModel').disabled,true);
  await ui.click('allDevicesOn');
  assert.equal(ui.calls.filter(call=>call.url === '/api/rooms/r1/devices').length,1);
  const next=snapshot(2);next.rooms.r1.active_count=1;next.rooms.r1.current=.1;next.rooms.r1.devices[0].is_on=true;
  ui.succeed(next);await first;
  assert.equal(ui.elements.get('roomActive').textContent,1);
  assert.equal(ui.elements.get('switch-light').attrs['aria-checked'],'true');
  assert.equal(ui.elements.get('allDevicesOn').disabled,true);
  assert.equal(ui.elements.get('switch-light').disabled,false);
});

test('legacy and disconnected states block bulk commands and settings controls',async()=>{
  const room=harness('r1');await flush();room.update(snapshot(2,'legacy'));
  await room.click('allDevicesOn');
  assert.equal(room.calls.length,1);
  assert.equal(room.elements.get('allDevicesOn').disabled,true);
  assert.equal(room.elements.get('switch-light').disabled,true);
  const settings=harness();await flush();settings.socket.disconnect();
  settings.click('resetSettings');
  assert.equal(settings.elements.get('resetSettingsDialog').open,undefined);
  assert.equal(settings.elements.get('saveSettings').disabled,true);
});
