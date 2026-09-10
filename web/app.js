'use strict';
const $=id=>document.getElementById(id);
let lang=location.pathname==='/judge'||new URLSearchParams(location.search).get('lang')==='en'?'en':(localStorage.getItem('loopcheck-language')||'zh');
let state,selectedRun,currentRun,currentView='work',refreshing=false,toastTimer,lastAttention,lastRefresh=0,lastRender;
const T=(zh,en)=>lang==='en'?en:zh;
const originalText=new WeakMap(),running=r=>r&&['queued','running'].includes(r.state);
const statusCopy={queued:['等待执行','Queued','neutral'],running:['正在执行','Running','working'],ready:['验收通过 · 待采用','Verified · review patch','success'],adopted:['已采用并保存','Adopted','success'],passed:['检查通过','Checks passed','success'],issues_found:['发现问题','Issues found','warning'],not_reproduced:['未复现问题','Not reproduced','warning'],repair_failed:['修复未通过','Repair incomplete','warning'],error:['本次未完成','Run stopped','error'],interrupted:['任务已中断','Interrupted','warning'],cancelled:['已停止','Stopped','neutral']};
const checkNames={add_toggle:'Adding and completing tasks',duplicate_identity:'Keep the other identically named task',mixed_order:'Delete only the selected item in a mixed list',persistence:'Preserve tasks and completion after reload'};
const eventTranslations=[['准备原版本','Preparing an immutable snapshot and isolated browser.'],['正在请求模型','Requesting the model; reserving this request’s cost.'],['读取 app.js','Reading app.js and the fixed page structure.'],['在隔离浏览器','Reproducing the issue in a real isolated browser.'],['把本次问题','Defining a reusable behavioral check.'],['在副本应用','Patching a copy and checking existing behavior.'],['执行已保存','Replaying saved requirements and independent checks.'],['检查完成','Browser checks finished. No model call or code change.'],['修复与旧功能','Independent checks passed. Review the patch before adopting.'],['尚未得到','No independently passing patch yet. Nothing was adopted.'],['未能复现','The issue was not reproduced; source is unchanged.'],['8 次','The eight-request limit was reached. Narrow the issue and retry.'],['费用上限','Model budget reached. Check usage before continuing.'],['认证或权限','Model access was rejected. Check the Beijing key and permissions.'],['额度不足','Model quota or rate limit reached. No paid fallback.'],['超时','A step timed out. Nothing was adopted.'],['已停止','The run stopped. Already sent requests may still be billed.'],['未完成','The run did not complete. Inspect evidence and retry a narrower issue.']];
function translated(text){
 if(lang!=='en'||!/[\u3400-\u9fff]/.test(text||''))return text||'';
 const known=eventTranslations.find(([key])=>text.includes(key));if(known)return known[1];
 const count=text.match(/预期 (\d+) 条任务，实际 (\d+) 条/);if(count)return 'Expected '+count[1]+' tasks; observed '+count[2]+'.';
 if(text.startsWith('已验收修复'))return 'Verified repair · '+text.split('·').at(-1).trim();
 if(text.startsWith('初始示例'))return 'Initial example · duplicate deletion bug';
 if(text.startsWith('文件变化'))return 'File change · '+text.split('·').at(-1).trim();
 for(const s of Object.values(state?.scenarios||{}))if(text.includes(s.name))return 'Original scenario · '+s.name_en;
 return text;
}
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function toast(text){$('toast').textContent=translated(text);$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,6000);}
async function api(url,body){
 const response=await fetch(url,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 let data;try{data=await response.json();}catch{throw new Error(T('服务没有响应，请重新连接。','The service did not respond. Reconnect to continue.'));}
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:T('请检查输入格式。','Check the input format.'));
 return data;
}
function translateStatic(){
 document.documentElement.lang=lang==='en'?'en':'zh-CN';
 document.querySelectorAll('[data-en]').forEach(n=>{if(!originalText.has(n))originalText.set(n,n.textContent);n.textContent=lang==='en'?n.dataset.en:originalText.get(n);});
 $('language-button').textContent=lang==='en'?'中文':'English';
}
function setView(name,scroll=true){
 currentView=name;document.querySelectorAll('[data-view]').forEach(n=>n.hidden=n.dataset.view!==name);
 document.querySelectorAll('[data-nav]').forEach(n=>{n.classList.toggle('selected',n.dataset.nav===name);n.setAttribute('aria-current',n.dataset.nav===name?'page':'false');});
 $('view-name').textContent={work:T('修复工作台','Repair'),guard:T('持续守护','Keep watch'),requirements:T('保存的验收','Saved checks'),versions:T('代码版本','Versions'),history:T('运行证据','Evidence')}[name];
 $('quickstart').hidden=name!=='work'||!!state?.requirements.length;
 if(scroll)window.scrollTo({top:0,behavior:'instant'});
}
function badge(value){const s=statusCopy[value]||['等待开始','Ready to start','neutral'];return el('span','status-pill '+s[2],T(s[0],s[1]));}
function fmtDate(value){return new Date(value*1000).toLocaleString(lang==='en'?'en-GB':'zh-CN',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});}
function setBusy(value){['repair-button','diagnose-button','recheck-button','load-scenario','import-file'].forEach(id=>$(id).disabled=value);$('repair-button').disabled=value||!state?.model.configured;}
function scenarioDescription(){const s=state?.scenarios[$('scenario-select').value];return s?(lang==='en'?s.symptom_en:s.symptom):'';}
function updateCount(){$('character-count').textContent=$('symptom').value.length+' / 1200';}
async function refresh(selectLatest=false){
 if(refreshing)return;refreshing=true;
 try{
  state=await api('/api/state');lastRefresh=Date.now();$('connection-notice').hidden=true;$('model-notice').hidden=state.model.configured;
  $('active-version').textContent=translated(state.version.name);$('current-code').textContent=state.version.code;
  $('stat-rules').textContent=$('nav-count').textContent=state.requirements.length;
  $('stat-auto').textContent=state.runs.filter(r=>['file_change','guard_repair'].includes(r.trigger)).length;
  $('stat-runs').textContent=state.runs.length+T(' 次运行留有证据',' recorded runs');
  $('stat-cost').textContent='¥'+state.budget.reported_cny.toFixed(4);
  $('budget-caption').textContent=T('上限 ¥','Limit ¥')+state.budget_limit_cny+(state.budget.unknown_reserved_cny?T(' · 另预留 ¥',' · reserved ¥')+state.budget.unknown_reserved_cny.toFixed(4):'');
  $('model-label').textContent=state.model.model+' · '+T('百炼北京','Model Studio Beijing');
  if(!$('scenario-select').options.length){
   Object.entries(state.scenarios).forEach(([key,s])=>$('scenario-select').add(new Option(lang==='en'?s.name_en:s.name,key)));
   const match=Object.entries(state.scenarios).find(([key,s])=>state.version.name.includes(s.name)||state.version.name.includes(s.name_en));
   $('scenario-select').value=match?.[0]||localStorage.getItem('loopcheck-scenario')||'duplicates';
   const latest=state.runs.find(r=>r.mode==='repair'&&(r.base_version===state.version.id||r.adopted_version===state.version.id)&&r.language===lang);
   $('symptom').value=localStorage.getItem('loopcheck-draft-'+lang)||latest?.symptom||scenarioDescription();updateCount();
  }
  renderRequirements();renderVersions();renderHistory();renderGuard();
  if(selectLatest&&!selectedRun&&state.runs.length)selectedRun=state.runs[0].id;
  if(selectedRun){const run=state.runs.find(r=>r.id===selectedRun);if(run)renderRun(run);}else renderEmpty();
  setBusy(state.busy);setView(currentView,false);
 }catch(error){$('connection-notice').hidden=false;setBusy(true);}finally{refreshing=false;}
}
function renderEmpty(){
 $('run-status').textContent=T('等待开始','Ready to start');const box=el('div','empty-progress');
 box.append(el('div','empty-icon','↻'),el('h3','',T('从一个具体问题开始','Start with one specific bug')),el('p','',T('实际工具操作和验证结果会显示在这里。','Actual tools and browser results appear here during the run.')));$('event-log').replaceChildren(box);
 $('checks-content').replaceChildren(el('div','empty-inline',T('运行一次检查，即可查看真实结果。','Run a check to see real browser evidence.')));
}
function checkLabel(c){return lang==='en'?(checkNames[c.id]||(/[\u3400-\u9fff]/.test(c.label)?'Saved behavioral check '+(Number(c.id.replace('requirement_',''))+1):c.label)):c.label;}
function allBefore(run){const checks=[...(run.before?.checks||[])],b=run.requirement_before?.checks?.[0],a=run.after?.checks?.at(-1);if(b&&a&&run.requirement&&!checks.some(c=>c.id===a.id))checks.push({...b,id:a.id});return checks;}
function renderRun(run){
 const renderKey=JSON.stringify([run.id,run.state,run.events.length,run.before?.total,run.after?.passed,run.edits,run.human_seconds,run.baseline_seconds,lang,state.busy,state.version.id]);
 if(lastRender===renderKey){currentRun=run;$('run-duration').textContent=(run.seconds??Math.floor(Date.now()/1000-run.created))+T(' 秒',' s');return;}
 lastRender=renderKey;
 currentRun=run;const b=badge(run.state);$('run-status').className=b.className;$('run-status').textContent=b.textContent;
 $('model-label').textContent=run.mode==='repair'?state.model.model+' · '+T('百炼北京','Model Studio Beijing'):T('仅浏览器检查 · 无模型费用','Browser checks only · No model cost');
 const signature=run.id+':'+run.events.length+':'+lang;
 if($('event-log').dataset.signature!==signature){const rows=run.events.map(event=>{const row=el('div','log-line '+(event.kind||''));row.append(el('time','log-time',new Date(event.time*1000).toLocaleTimeString('en-GB')),el('span','log-icon',event.kind==='success'?'✓':'·'),el('span','',translated(event.message)));return row;});$('event-log').replaceChildren(...rows);$('event-log').dataset.signature=signature;$('event-log').scrollTop=$('event-log').scrollHeight;}
 const flags={read:run.tool_calls.includes('read_project'),reproduce:!!run.before,requirement:!!run.requirement,edit:!!run.after?.all_passed,adopt:run.state==='adopted'};
 document.querySelectorAll('[data-stage]').forEach(n=>n.classList.toggle('done',flags[n.dataset.stage]));
 $('run-duration').textContent=(run.seconds??Math.floor(Date.now()/1000-run.created))+T(' 秒',' s');
 $('cancel-button').hidden=!running(run);
 $('result-description').textContent=run.error?translated(run.error):T('浏览器检查决定是否通过；以下是实际执行结果。','Passing is determined by browser checks. These are actual results.');
 const ready=run.state==='ready',adopted=run.state==='adopted';
 $('decision-summary').hidden=!ready&&!adopted&&!['issues_found','repair_failed','error','cancelled','not_reproduced'].includes(run.state);
 $('decision-summary').classList.toggle('warning-summary',!ready&&!adopted);
 $('decision-title').textContent=ready?T('修复已通过，等待你的决定。','Verified. Ready for your decision.'):adopted?T('已采用。这个问题现在有了可复用的检查。','Adopted. This bug now has a reusable check.'):T('原版本保留，可查看原因后继续。','Your previous version is safe. Review what happened.');
 $('decision-text').textContent=ready?run.after.passed+' / '+run.after.total+T(' 项检查通过。采用后保存补丁和行为要求。',' checks passed. Adoption saves the patch and its behavioral check.'):adopted?T('到“持续守护”开启后台复查，或下载当前版本。','Enable Keep watch for background checks, or download this version.'):run.error?translated(run.error):T('查看失败行为，缩小问题范围，或换一个原创场景重试。','Inspect failed behaviors, narrow the issue, or try another scenario.');
 $('adopt-button').hidden=!ready;$('adopt-button').disabled=state.busy||run.base_version!==state.version.id;
 if(ready&&run.base_version!==state.version.id)$('decision-text').textContent=T('当前版本已变化，请在新版本上重新验证。','The active version changed. Verify the new version before adopting.');
 $('download-patch').hidden=!run.diff;$('download-patch').href='/api/runs/'+run.id+'/patch';
 $('download-report').hidden=running(run);$('download-report').href='/api/runs/'+run.id+'/report';$('timing-panel').hidden=running(run);
 for(const [id,value]of[['human-minutes',run.human_seconds],['baseline-minutes',run.baseline_seconds]])if(document.activeElement!==$(id))$(id).value=value==null?'':(value/60).toFixed(1);
 $('timing-comparison').textContent=run.baseline_seconds>0&&run.human_seconds!=null?T('你的自报对照：','Your self-report: ')+run.baseline_seconds+' s → '+run.human_seconds+' s. '+T('仅代表这次记录，不等于普遍提效效果。','This record does not establish a general efficiency gain.'):'';
 renderChecks(run);renderScreenshotOptions(run);renderScreenshots();renderDiff(run);
}
function renderChecks(run){
 const before=allBefore(run),after=run.after?.checks||[],root=$('checks-content');
 if(!before.length&&!after.length){root.replaceChildren(el('div','empty-inline',T('检查结果准备中…','Waiting for browser evidence…')));return;}
 const head=el('div','check-row check-head');head.append(el('span','',T('独立行为检查','Independent behavior')),el('span','check-state',T('之前','Before')),el('span','check-state',T('之后','After')));root.replaceChildren(head);
 for(const id of new Set([...before.map(c=>c.id),...after.map(c=>c.id)])){
  const b=before.find(c=>c.id===id),a=after.find(c=>c.id===id),row=el('div','check-row'),label=el('div','check-label',checkLabel(a||b)),detail=el('details','check-detail');
  detail.append(el('summary','',T('操作与结果','Inspect observed behavior')));
  for(const [name,c]of[[T('之前：','Before: '),b],[T('之后：','After: '),a]])detail.append(el('p','',name+(c?(lang==='en'&&c.passed?'PASS · '+checkLabel(c):translated(c.actual)):T('未执行','Not run'))));
  label.append(detail);row.append(label);[b,a].forEach(c=>row.append(el('span','check-state '+(!c?'missing':c.passed?'pass':'fail'),!c?'—':c.passed?T('✓ 通过','✓ Pass'):T('! 失败','! Fail'))));root.append(row);
 }
}
function renderScreenshotOptions(run){
 const checks=[...allBefore(run),...(run.after?.checks||[])],seen=new Set(),selected=$('screenshot-select').value;
 $('screenshot-select').replaceChildren();for(const c of checks)if(!seen.has(c.id)){seen.add(c.id);$('screenshot-select').add(new Option(checkLabel(c),c.id));}
 $('screenshot-select').value=seen.has(selected)?selected:(checks.find(c=>!c.passed)?.id||checks[0]?.id||'');
}
function renderScreenshots(){
 if(!currentRun)return;const root=$('screenshots-content');root.replaceChildren();
 for(const [label,checks]of[[T('原版本 · 实际复现','Before · observed behavior'),allBefore(currentRun)],[T('修改后 · 独立验证','After · independent verification'),currentRun.after?.checks||[]]]){
  const fig=el('figure','evidence-item'),c=checks.find(c=>c.id===$('screenshot-select').value);fig.append(el('figcaption','',label));
  if(c?.image){const link=el('a');link.href=c.image;link.target='_blank';link.rel='noopener';const img=el('img');img.src=c.image;img.alt=label+': '+checkLabel(c);img.loading='lazy';link.append(img);fig.append(link);}
  else fig.append(el('div','evidence-placeholder',T('此阶段还未执行该检查','This check has not run in this phase.')));root.append(fig);
 }
}
function renderDiff(run){
 $('edit-reason').textContent=lang==='en'?'Exact source changes produced by the model. See independent checks for verification.':(run.edit_reason||'');$('diff-content').replaceChildren();
 if(!run.diff){$('diff-content').textContent=T('尚无代码修改。','No code changes.');return;}run.diff.split('\n').forEach(line=>$('diff-content').append(el('span',line.startsWith('+')?'diff-add':line.startsWith('-')?'diff-remove':'',line+'\n')));
}
function stepText(s){const n=s.index+1;return{add:T('新增：','Add: ')+s.value,delete:T('删除第 ','Delete item ')+n,toggle:T('将第 ','Set item ')+n+T(' 条设为',' to ')+(s.done?T('已完成','complete'):T('未完成','incomplete')),reload:T('刷新页面','Reload the page'),expect_count:T('确认任务数为 ','Expect task count: ')+s.count,expect_title:T('确认第 ','Expect item ')+n+T(' 条内容为：',' title: ')+s.value,expect_done:T('确认第 ','Expect item ')+n+(s.done?T(' 条已完成',' is complete'):T(' 条未完成',' is incomplete'))}[s.action];}
function renderRequirements(){
 const root=$('requirements-list');root.replaceChildren();if(!state.requirements.length){root.append(el('div','empty-inline',T('采用第一个通过验收的修复后，这里会保存对应的检查。','Adopt your first verified patch to save its behavioral check here.')));return;}
 for(const r of state.requirements){const row=el('article','item-row'),info=el('div'),detail=el('details'),list=el('ol','steps');r.spec.steps.forEach(s=>list.append(el('li','',stepText(s))));info.append(el('h3','',lang==='en'&&/[\u3400-\u9fff]/.test(r.title)?'Saved behavioral check':r.title),el('p','',r.spec.steps.length+T(' 个操作与断言 · ',' actions and assertions · ')+fmtDate(r.created)));detail.append(el('summary','',T('查看可执行步骤','See executable steps')),list);info.append(detail);row.append(info,el('span','status-pill success',T('改版后复用','Reusable')));root.append(row);}
}
function renderVersions(){
 const root=$('versions-list');root.replaceChildren();
 for(const v of state.versions){const row=el('article','item-row'),info=el('div'),actions=el('div','result-actions');info.append(el('h3','',translated(v.name)),el('p','',fmtDate(v.created)+' · '+v.hash.slice(0,10)));const download=el('a','button secondary compact',T('下载完整示例','Download app'));download.href='/api/versions/'+v.id+'/download';actions.append(download);
 if(v.id===state.version.id)actions.append(el('span','status-pill success',T('当前版本','Current version')));else{const b=el('button','button secondary compact',T('切换并复查','Restore & check'));b.disabled=state.busy;b.onclick=()=>changeVersion({action:'switch',version_id:v.id});actions.append(b);}row.append(info,actions);root.append(row);}
}
function renderHistory(){
 const filter=$('history-filter').value,root=$('history-list');root.replaceChildren();
 const runs=state.runs.filter(r=>filter==='all'||filter==='repair'&&r.mode==='repair'||filter==='automatic'&&['file_change','guard_repair'].includes(r.trigger)||filter==='needs_attention'&&['ready','error','repair_failed','issues_found'].includes(r.state));
 if(!runs.length){root.append(el('div','empty-inline',T('这里还没有符合条件的记录。','No runs match this filter yet.')));return;}
 for(const r of runs){const row=el('article','item-row'),info=el('div'),actions=el('div','result-actions');info.append(el('h3','',({repair:T('AI 修复','AI repair'),diagnose:T('复现检查','Diagnosis'),recheck:T('版本复查','Version check')}[r.mode])+' · '+fmtDate(r.created)),el('p','',(r.seconds??'…')+' s · '+T('模型请求 ','Model requests: ')+(r.usage?.calls||0)+' · ¥'+(r.usage?.reported_cny||0).toFixed(4)+(r.trigger&&r.trigger!=='manual'?T(' · 后台触发',' · Background trigger'):'')));
 const b=el('button','button secondary compact',T('查看证据','Inspect'));b.onclick=()=>{selectedRun=r.id;renderRun(r);setView('work');$('result-heading').scrollIntoView({block:'start'});};const report=el('a','subtle-link',T('报告 ↓','Report ↓'));report.href='/api/runs/'+r.id+'/report';actions.append(badge(r.state),b,report);row.append(info,actions);root.append(row);}
}
function renderGuard(){
 const g=state.guard,labels={off:T('尚未开启','Off'),watching:T('正在守护','Watching'),changed:T('发现文件变化','File changed'),checking:T('后台检查中','Checking'),repairing:T('自动准备补丁','Preparing patch'),review:T('需要查看结果','Review result'),blocked:T('需要处理','Needs attention'),conflict:T('文件冲突 · 已暂停','File conflict · paused')};
 $('guard-status').textContent=labels[g.phase]||g.phase;$('guard-status').className='status-pill '+(g.enabled?'success':'neutral');
 $('guard-toggle').textContent=g.enabled?T('暂停守护','Pause watching'):T('开启持续守护','Start watching');$('guard-toggle').disabled=!g.enabled&&!state.requirements.length;
 $('guard-auto').disabled=g.enabled;if(g.enabled)$('guard-auto').checked=g.auto_repair;
 $('guard-message').textContent=g.message?(lang==='en'?'The watched file needs attention. Check its format or restart watching; pending edits are not overwritten.':g.message):!state.requirements.length?T('先采用一个通过验收的修复，即可开启。','Adopt one verified repair to enable watching.'):g.enabled?T('只有文件内容变化时才执行，不反复消耗模型额度。','Only content changes trigger work. No repeated model calls while unchanged.'):'';
 $('guard-dot').hidden=!g.enabled;$('guard-path-box').hidden=!g.enabled||!g.path;$('guard-path').value=g.path||'';$('guard-demo').disabled=!g.enabled||state.busy;
 const run=state.runs.find(r=>r.id===g.last_run),attention=g.enabled&&run&&!running(run)&&['ready','issues_found','error','repair_failed'].includes(run.state);
 $('attention-banner').hidden=!attention;if(attention){$('attention-title').textContent=run.state==='ready'?T('守护发现了回归，修复已准备好。','A regression was caught. Your verified patch is ready.'):T('后台检查有结果需要你查看。','A background check needs your attention.');$('attention-text').textContent=T('无需重复描述问题；查看证据后决定下一步。','No repeated bug report needed. Review the evidence and decide.');if(lastAttention!==run.id){lastAttention=run.id;document.title='● LoopCheck · '+T('需要查看','Review ready');}}
}
async function runMode(mode){
 if(!state)return;setBusy(true);$('cancel-button').disabled=false;
 try{const run=await api('/api/runs',{mode,symptom:mode==='repair'?$('symptom').value:'',expected_version:state.version.id,language:lang});selectedRun=run.id;setView('work',false);renderRun(run);$('run-status').scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});await refresh();}catch(e){toast(e.message);setBusy(state.busy);}
}
async function changeVersion(fields){setBusy(true);try{const result=await api('/api/versions',{expected_version:state.version.id,language:lang,...fields});if(result.run)selectedRun=result.run.id;await refresh();setView('work');toast(T('版本已载入，正在自动复查。','Version loaded. Verification starts automatically.'));}catch(e){toast(e.message);setBusy(state.busy);}}
function selectTab(name,focus=false){document.querySelectorAll('[data-tab]').forEach(n=>{const s=n.dataset.tab===name;n.classList.toggle('active',s);n.setAttribute('aria-selected',String(s));n.tabIndex=s?0:-1;if(s&&focus)n.focus();});document.querySelectorAll('[data-panel]').forEach(n=>n.hidden=n.dataset.panel!==name);}
document.querySelectorAll('[data-nav]').forEach(n=>n.onclick=()=>setView(n.dataset.nav));document.querySelectorAll('[data-go]').forEach(n=>n.onclick=()=>setView(n.dataset.go));
document.querySelectorAll('[data-tab]').forEach(n=>{n.onclick=()=>selectTab(n.dataset.tab);n.onkeydown=e=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const tabs=['checks','screenshots','diff'],i=tabs.indexOf(n.dataset.tab);selectTab(e.key==='Home'?tabs[0]:e.key==='End'?tabs[2]:tabs[(i+(e.key==='ArrowRight'?1:2))%3],true);}};});
$('symptom').oninput=()=>{updateCount();localStorage.setItem('loopcheck-draft-'+lang,$('symptom').value);};$('symptom').onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&!$('repair-button').disabled){e.preventDefault();runMode('repair');}};
$('scenario-select').onchange=()=>{localStorage.setItem('loopcheck-scenario',$('scenario-select').value);$('symptom').value=scenarioDescription();localStorage.setItem('loopcheck-draft-'+lang,$('symptom').value);updateCount();};$('load-scenario').onclick=()=>changeVersion({action:'scenario',scenario_id:$('scenario-select').value});
$('repair-button').onclick=()=>runMode('repair');$('diagnose-button').onclick=()=>runMode('diagnose');$('recheck-button').onclick=()=>runMode('recheck');$('screenshot-select').onchange=renderScreenshots;$('history-filter').onchange=renderHistory;
$('adopt-button').onclick=async()=>{try{await api('/api/runs/'+selectedRun+'/adopt',{expected_version:state.version.id});await refresh();toast(T('已采用并保存验收，可以开启持续守护。','Adopted and remembered. You can now enable Keep watch.'));}catch(e){toast(e.message);}};
$('cancel-button').onclick=async()=>{try{await api('/api/runs/'+selectedRun+'/cancel',{});$('cancel-button').disabled=true;toast(T('已请求停止，会在当前调用或检查结束后停止。','Stop requested. The current model or browser step must finish first.'));}catch(e){toast(e.message);}};
$('guard-toggle').onclick=async()=>{try{await api('/api/guard',{enabled:!state.guard.enabled,auto_repair:$('guard-auto').checked,language:lang});await refresh();}catch(e){toast(e.message);}};
$('guard-demo').onclick=async()=>{try{await api('/api/guard/change',{scenario_id:'duplicates'});toast(T('已保存有意引入回归的文件，守护会自动发现。','A disclosed regression was saved. The agent will detect it.'));await refresh();}catch(e){toast(e.message);}};
$('review-guard').onclick=()=>{selectedRun=state.guard.last_run;const run=state.runs.find(r=>r.id===selectedRun);if(run)renderRun(run);setView('work');$('result-heading').scrollIntoView({block:'start'});document.title='LoopCheck';};
$('copy-path').onclick=async()=>{try{await navigator.clipboard.writeText($('guard-path').value);toast(T('文件路径已复制。','File path copied.'));}catch{$('guard-path').focus();$('guard-path').select();toast(T('请复制已选中的路径。','Copy the selected path.'));}};
$('import-file').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{if(f.size>16000)throw new Error(T('app.js 不能超过 16000 字节。','app.js must be under 16000 bytes.'));await changeVersion({action:'import',code:await f.text(),name:T('导入 · ','Imported · ')+f.name});}catch(err){toast(err.message);}e.target.value='';};
$('save-timing').onclick=async()=>{try{if($('human-minutes').value==='')throw new Error(T('请填写实际人工用时。','Enter your actual assisted time.'));await api('/api/runs/'+selectedRun+'/timing',{human_seconds:Number($('human-minutes').value)*60,baseline_seconds:$('baseline-minutes').value===''?null:Number($('baseline-minutes').value)*60});await refresh();toast(T('已保存自报时间，报告中会明确标注。','Self-reported time saved and labeled in the report.'));}catch(e){toast(e.message);}};
function help(setup=false){$('setup-help').hidden=!setup;$('help-dialog').showModal();}
$('help-button').onclick=()=>help();$('tour-button').onclick=()=>help();$('setup-button').onclick=()=>help(true);$('close-help').onclick=()=>$('help-dialog').close();
$('language-button').onclick=()=>{lang=lang==='en'?'zh':'en';localStorage.setItem('loopcheck-language',lang);translateStatic();if(state){[...$('scenario-select').options].forEach(o=>o.textContent=lang==='en'?state.scenarios[o.value].name_en:state.scenarios[o.value].name);$('symptom').value=localStorage.getItem('loopcheck-draft-'+lang)||scenarioDescription();updateCount();}refresh();};
$('retry-connection').onclick=()=>refresh(true);window.addEventListener('focus',()=>refresh());
setInterval(()=>{if(!document.hidden&&(state?.busy||state?.guard.enabled||Date.now()-lastRefresh>15000))refresh();},1500);
translateStatic();refresh(true);

