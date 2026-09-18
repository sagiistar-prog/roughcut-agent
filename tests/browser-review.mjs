import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import http from 'node:http';

const root = process.cwd(), port = 8891;
const server = spawn(process.env.PYTHON || 'python',['scripts/review_server.py','--port',String(port)],{cwd:root,stdio:'pipe'});
const base = `http://127.0.0.1:${port}`;
const output = path.join(root,'output','browser-' + Date.now());
await fs.mkdir(output,{recursive:true});
await fs.mkdir('.impeccable/review',{recursive:true});
let browser;
const reports = [];
try {
  for (let i=0; i<40; i++) { try { if ((await fetch(base)).ok) break; } catch {} await new Promise(r=>setTimeout(r,100)); }
  assert.equal((await fetch(base + '/raw/test.mp4')).status,404);
  const externalStatus = await new Promise((resolve,reject)=>http.get(base,{headers:{Host:'external.invalid'}},res=>{res.resume();resolve(res.statusCode);}).on('error',reject));
  assert.equal(externalStatus,403);
  browser = await chromium.launch({channel:process.env.BROWSER_CHANNEL || undefined, headless:true});
  for (const width of [1440,390]) {
    const context = await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce',acceptDownloads:true});
    const page = await context.newPage(), errors = []; let cancelReplace = false; page.on('pageerror',e=>errors.push(e.message)); page.on('dialog', d=>cancelReplace ? d.dismiss() : d.accept());
    await page.goto(base); await page.getByRole('button',{name:'打开示例',exact:true}).click(); await page.locator('.clip').first().waitFor();
    const count = await page.locator('.clip').count(); assert.ok(count>2);
    assert.equal(await page.getByRole('button',{name:'导出审核时间线',exact:true}).isDisabled(),true);
    await page.getByRole('checkbox',{name:'保留片段 1',exact:true}).uncheck();
    assert.equal(await page.getByRole('checkbox',{name:'保留片段 1',exact:true}).isChecked(),false);
    await page.getByRole('button',{name:'撤销',exact:true}).click();
    assert.equal(await page.getByRole('checkbox',{name:'保留片段 1',exact:true}).isChecked(),true);
    const first = await page.locator('.clip-main > p:first-of-type').first().textContent();
    await page.getByRole('button',{name:'下移片段 1',exact:true}).click(); assert.equal(await page.locator('.clip-main > p:first-of-type').nth(1).textContent(),first);
    await page.getByRole('button',{name:'撤销',exact:true}).click();
    await page.getByLabel('入点 / 秒').fill('2'); await page.getByLabel('出点 / 秒').fill('1'); await page.getByRole('button',{name:'应用切点',exact:true}).click();
    assert.match(await page.locator('#trim-status').textContent(),/切点无效/);
    await page.getByLabel('入点 / 秒').fill('1'); await page.getByLabel('出点 / 秒').fill('7'); await page.getByRole('button',{name:'应用切点',exact:true}).click();
    assert.match(await page.locator('#trim-status').textContent(),/已更新/);
    cancelReplace = true;
    await page.getByRole('button',{name:'打开示例',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('已保留当前草稿'));
    assert.equal(await page.locator('#end').inputValue(),'7');
    await page.locator('#import-file').setInputFiles(path.join(root,'examples/review-demo.json'));
    assert.equal(await page.locator('#end').inputValue(),'7');
    cancelReplace = false;
    await page.locator('#import-file').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('{}')});
    assert.match(await page.locator('#status').textContent(),/原草稿已保留/); assert.equal(await page.locator('#end').inputValue(),'7');
    const savedEvent = page.waitForEvent('download'); await page.getByRole('button',{name:'保存审核会话',exact:true}).click(); const saved = await savedEvent;
    const sessionFile = path.join(output,`session-${width}.json`); await saved.saveAs(sessionFile);
    await page.locator('#import-file').setInputFiles(sessionFile); assert.equal(await page.locator('#end').inputValue(),'7');
    for (let i=1;i<=count;i++) await page.getByRole('checkbox',{name:`保留片段 ${i}`,exact:true}).uncheck();
    await page.getByLabel('我已核对所选片段和切点').check(); assert.equal(await page.locator('#export').isDisabled(),true);
    await page.getByRole('checkbox',{name:'保留片段 1',exact:true}).check();
    await page.getByLabel('我已核对所选片段和切点').check();
    const csvEvent = page.waitForEvent('download'); await page.locator('#export').click(); const csv = await csvEvent;
    const csvPath = path.join(output,`sample-${width}.csv`); await csv.saveAs(csvPath); assert.match(await fs.readFile(csvPath,'utf8'),/"1","7","6"/);
    await page.getByRole('button',{name:'打开示例',exact:true}).click(); await page.waitForFunction(()=>document.querySelector('#project-name').textContent==='虚构示例');
    await page.getByRole('button',{name:'查看片段 2',exact:true}).focus(); await page.keyboard.press('Enter');
    if (width===1440) assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-label')),'查看片段 2');
    else { assert.equal(await page.evaluate(()=>document.activeElement.id),'preview-pane'); await page.locator('#back').click(); assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-label')),'查看片段 2'); }
    await page.getByRole('button',{name:'查看片段 1',exact:true}).focus(); await page.keyboard.press('Space');
    if (width===1440) assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-label')),'查看片段 1');
    await page.locator('#media-file').setInputFiles({name:'wrong.mp4',mimeType:'video/mp4',buffer:Buffer.from('invalid media')});
    assert.match(await page.locator('#media-state').textContent(),/请选择与当前片段/);
    await page.locator('#media-file').setInputFiles({name:'demo_001.mp4',mimeType:'video/mp4',buffer:Buffer.from('invalid media')});
    await page.waitForFunction(()=>document.querySelector('#media-state').textContent.includes('无法播放'));
    assert.equal(await page.locator('#play').isDisabled(),true);
    await page.getByRole('button',{name:'打开示例',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#media-state').textContent.includes('仅在当前页面'));
    assert.equal(await page.locator('#media-state').getAttribute('class'),'');
    assert.equal((await page.locator('#export-help').textContent()).includes('已导出'),false);
    assert.equal(await page.locator('#export-help').getAttribute('role'),'status');
    const axe = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze(); assert.deepEqual(axe.violations.map(x=>x.id),[]);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth > innerWidth),false);
    assert.equal((await page.locator('body').innerText()).includes('·'),false);
    await page.evaluate(()=>scrollTo(0,0)); await page.screenshot({path:`.impeccable/review/${width===1440?'desktop':'mobile'}.png`,fullPage:true});
    if (process.env.ROUGHCUT_REAL_TIMELINE && width===1440) {
      const input = path.resolve(process.env.ROUGHCUT_REAL_TIMELINE);
      const data = JSON.parse(await fs.readFile(input,'utf8'));
      const realSource = data.result.candidates.find(item=>item.clip).clip.source_file;
      await page.locator('#media-file').setInputFiles({name:'demo_001.mp4',mimeType:'video/mp4',buffer:await fs.readFile(path.resolve(realSource))});
      await page.waitForFunction(()=>document.querySelector('#media-state').textContent.includes('时长不匹配'));
      assert.equal(await page.locator('#play').isDisabled(),true);
      await page.locator('#import-file').setInputFiles(input); await page.waitForFunction(()=>document.querySelector('#project-name').textContent==='导入的审核');
      const source = data.result.candidates.find(item=>item.clip).clip.source_file;
      await page.locator('#media-file').setInputFiles(path.resolve(source));
      await page.waitForFunction(()=>!document.querySelector('#play').disabled);
      await page.locator('#play').click(); await page.waitForFunction(()=>!document.querySelector('#video').paused && document.querySelector('#video').currentTime > .1);
      await page.locator('#play').click();
      const start = Number(await page.locator('#start').inputValue());
      await page.locator('#start').fill(String(round(start+.1))); await page.locator('#trim button').click();
      await page.getByLabel('我已核对所选片段和切点').check();
      const realEvent = page.waitForEvent('download'); await page.locator('#export').click(); const realCSV = await realEvent;
      const realDir = path.join(output,'reviewed'); await fs.mkdir(realDir);
      await realCSV.saveAs(path.join(realDir,'timeline_review.csv'));
      reports.push({real_media_played:true,reviewed_timeline:path.relative(root,path.join(realDir,'timeline_review.csv'))});
    }
    assert.deepEqual(errors,[]); reports.push({width,axe_violations:0,page_errors:0,overflow:false,review_actions:'import/select/restore/reorder/undo/trim/session/invalid input/empty/export'});
    await context.close();
  }
  await fs.writeFile(path.join(output,'browser-report.json'),JSON.stringify(reports,null,2));
  console.log(JSON.stringify({output:path.relative(root,output),reports},null,2));
} finally { await browser?.close(); server.kill(); }
function round(n){return Math.round(n*1000)/1000;}
