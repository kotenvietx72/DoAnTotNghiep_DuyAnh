// E2E trên backend/profile mới, SQLite riêng và Telegram tắt; không dùng phiên người dùng.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const net=require('node:net');
const {spawn}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE||'playwright');
const root=path.resolve(__dirname,'..');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function main(){
  fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  const output=fs.mkdtempSync(path.join(root,'test-results','room-ui-'));
  const port=await new Promise(resolve=>{const listener=net.createServer();listener.listen(0,'127.0.0.1',()=>{const port=listener.address().port;listener.close(()=>resolve(port));});});
  const origin=`http://127.0.0.1:${port}`;
  const python=process.env.WEB_PYTHON||path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
  const server=spawn(python,['app.py'],{cwd:root,windowsHide:true,
    env:{...process.env,HOST:'127.0.0.1',PORT:String(port),ROOM_DATABASE:path.join(output,'rooms.sqlite3'),TELEGRAM_ENABLED:'0',PYTHON_DOTENV_DISABLED:'1',PYTHONUTF8:'1'}});
  let logs='';server.stdout.on('data',data=>{logs+=data;});server.stderr.on('data',data=>{logs+=data;});
  let browser;
  const results=[];
  try{
    let ready=false;
    for(let i=0;i<100;i++){
      try{if((await fetch(`${origin}/api/state`)).ok){ready=true;break;}}catch{}
      if(server.exitCode!==null) throw new Error('Test server exited');
      await delay(100);
    }
    assert.ok(ready,'Test server failed to start');
    browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
    const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    for(const width of [1440,1024,390,320]){
      await page.setViewportSize({width,height:1100});
      await page.goto(origin);
      await page.locator('.room-preview [data-model-device]').last().waitFor();
      assert.equal(await page.locator('.room-preview [data-model-device]').count(),33);
      assert.equal(await page.locator('.room-preview button[data-model-device]').count(),0);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await page.screenshot({path:path.join(output,`home-${width}.png`),fullPage:true});
      for(const [id,count] of [['r1',14],['r2',11],['r3',8]]){
        await page.goto(`${origin}/rooms/${id}`);
        await page.locator('#roomModel button[data-model-device]').last().waitFor();
        await page.waitForFunction(()=>document.getElementById('connectionStatus').textContent.includes('Đã kết nối'));
        assert.equal(await page.locator('#roomModel button[data-model-device]').count(),count);
        assert.equal(await page.locator('#deviceList .device-code').count(),count);
        const geometry=await page.locator('#roomModel').evaluate(container=>{
          const nodes=[...container.querySelectorAll('[data-model-device]')];
          const collisions=[];
          for(let i=0;i<nodes.length;i++) for(let j=i+1;j<nodes.length;j++){
            const a=nodes[i].getBoundingClientRect(),b=nodes[j].getBoundingClientRect();
            if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1) collisions.push([nodes[i].dataset.modelDevice,nodes[j].dataset.modelDevice]);
          }
          const minTarget=Math.min(...nodes.map(node=>Math.min(node.getBoundingClientRect().width,node.getBoundingClientRect().height)));
          const scene=container.querySelector('.room-scene').getBoundingClientRect();
          const outside=nodes.filter(node=>{const r=node.getBoundingClientRect();return r.left<scene.left||r.right>scene.right||r.top<scene.top||r.bottom>scene.bottom;}).map(node=>node.dataset.modelDevice);
          return {collisions,minTarget,outside,height:scene.height};
        });
        const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
        results.push({width,id,...geometry,overflow});
        assert.deepEqual(geometry.collisions,[],JSON.stringify(results.at(-1)));
        assert.deepEqual(geometry.outside,[],JSON.stringify(results.at(-1)));
        assert.ok(geometry.minTarget>=44,JSON.stringify(results.at(-1)));
        assert.ok(!overflow,JSON.stringify(results.at(-1)));
        const clearDoor=await page.locator('#roomModel').evaluate(container=>{
          const door=container.querySelector('[data-main-door]').getBoundingClientRect();
          return [...container.querySelectorAll('.model-furniture,.model-chair')].every(node=>{
            const r=node.getBoundingClientRect();
            return Math.min(r.right,door.right)<=Math.max(r.left,door.left)||Math.min(r.bottom,door.bottom)<=Math.max(r.top,door.top);
          });
        });
        assert.ok(clearDoor,`Door blocked in ${id} at ${width}`);
        if(id==='r2'){
          const symmetric=await page.locator('#roomModel').evaluate(container=>{
            const scene=container.querySelector('.room-scene').getBoundingClientRect(),axis=scene.left+scene.width/2;
            const center=node=>{const r=node.getBoundingClientRect();return r.left+r.width/2;};
            const route=center(container.querySelector('[data-circulation]'));
            const beds=[...container.querySelectorAll('[data-bed]')].map(center);
            const lights=['light1','light2'].map(id=>center(container.querySelector(`[data-model-device="${id}"]`)));
            return Math.abs(route-axis)<1&&Math.abs(beds[0]+beds[1]-2*axis)<1&&lights.every((x,i)=>Math.abs(x-beds[i])<1);
          });
          assert.ok(symmetric,`Dormitory lost center alignment at ${width}`);
        }
        await page.evaluate(()=>scrollTo(0,0));
        await page.screenshot({path:path.join(output,`${id}-${width}.png`),fullPage:true});
      }
    }
    await page.setViewportSize({width:1440,height:1100});
    await page.goto(`${origin}/rooms/r1`);
    const control=page.locator('#roomModel [data-model-device="light1"]');
    await control.waitFor();
    await page.waitForFunction(()=>!document.querySelector('#roomModel [data-model-device="light1"]').disabled);
    const second=await browser.newPage();await second.goto(`${origin}/rooms/r1`);
    await second.locator('#roomModel [data-model-device="light1"]').waitFor();
    let commands=0;
    page.on('request',request=>{if(request.method()==='POST'&&request.url()===`${origin}/api/rooms/r1/devices/light1`) commands++;});
    await control.click();
    await page.waitForFunction(()=>document.querySelector('[data-device="light1"]').getAttribute('aria-checked')==='true');
    await second.waitForFunction(()=>document.querySelector('#roomModel [data-model-device="light1"]').getAttribute('aria-pressed')==='true');
    await control.press('Enter');
    await page.waitForFunction(()=>document.querySelector('[data-device="light1"]').getAttribute('aria-checked')==='false');
    await control.press('Space');
    await page.waitForFunction(()=>document.querySelector('[data-device="light1"]').getAttribute('aria-checked')==='true');
    assert.equal(commands,3,'Click/Enter/Space must each send exactly one command');
    await page.locator('#allDevicesOn').click();
    await page.waitForFunction(()=>document.getElementById('roomActive').textContent==='14');
    assert.equal(await page.locator('#roomModel .device-on').count(),14);
    await page.goto(origin);
    await page.locator('#simulationMode').selectOption('legacy');
    await page.locator('#btnStart').click();
    await page.waitForFunction(()=>!document.getElementById('btnStop').disabled);
    await page.locator('#btnStop').click();
    await page.waitForFunction(()=>document.getElementById('btnStop').disabled);
    const frozen=await (await fetch(`${origin}/api/state`)).json();
    for(const id of ['r1','r2','r3']){
      await page.goto(`${origin}/rooms/${id}`);
      await page.locator('#roomModel button').last().waitFor();
      assert.equal(await page.locator('#roomModel .device-on').count(),frozen.rooms[id].active_count);
      assert.equal(await page.locator('#roomModel button:disabled').count(),frozen.rooms[id].devices.length);
      assert.equal(await page.locator('#allDevicesOn').isDisabled(),true);
    }
    await page.goto(`${origin}/settings`);
    await page.waitForFunction(()=>!document.getElementById('saveSettings').disabled);
    await page.locator('#r1-warn').fill('3');
    await page.locator('#saveSettings').click();
    await page.waitForFunction(()=>document.getElementById('settingsMessage').textContent.includes('Đã lưu'));
    await page.locator('#resetSettings').click();
    await page.locator('#resetSettingsDialog').waitFor({state:'visible'});
    await page.locator('#cancelReset').click();
    assert.equal(await page.locator('#r1-warn').inputValue(),'3');
    await page.locator('#resetSettings').click();
    await page.locator('#confirmReset').click();
    await page.waitForFunction(()=>document.getElementById('settingsMessage').textContent.includes('Đã khôi phục'));
    assert.equal(await page.locator('#r1-warn').inputValue(),'12');
    assert.equal(await page.locator('#r3-warn').inputValue(),'6');
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(output,'report.json'),JSON.stringify({results,commands,errors,socketSync:true,bulk:true,legacy:true,settingsReset:true},null,2));
    console.log(JSON.stringify({output,viewports:4,roomViews:results.length,devices:33,commands,socketSync:true,bulk:true,legacy:true,settingsReset:true,errors}));
  }catch(error){console.error(logs.slice(-1800));throw error;}
  finally{if(browser)await browser.close();server.kill();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
