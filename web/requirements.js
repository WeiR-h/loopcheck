'use strict';
Object.assign(words.zh,{incomplete:'本次修改尚未完成验收',incompleteHelp:'实现缺失功能后，生成并确认检查步骤，再复查全部要求。',expect_hidden:'应当隐藏'});
Object.assign(words.en,{incomplete:'Acceptance is incomplete',incompleteHelp:'Implement missing behavior, generate and approve its checks, then recheck the full scope.',expect_hidden:'Must be hidden'});
const dual=(zh,en)=>language==='zh'?zh:en;
const latestCheck=()=>state.runs.find(r=>r.project_id===projectId&&r.mode==='check');
let editingRequirement=null, editingAction='add';
const originalRender=render;
render=function(){
  if(!disconnected)document.querySelectorAll('#workspace button').forEach(b=>b.disabled=false);
  originalRender();
  $('service-retry').hidden=!disconnected;
  $('download').setAttribute('aria-disabled',String(disconnected));$('download').tabIndex=disconnected?-1:0;
  const requirements=currentContract?.requirements||[], active=requirements.filter(r=>r.enabled), r=run();
  $('check').classList.toggle('primary',active.length>0);$('prepare').classList.toggle('primary',!active.length);
  $('add-requirement').disabled=!projectId||state.busy;
  $('bind-requirements').disabled=!active.some(r=>!r.flow)||state.busy;
  $('flow-count').textContent=`${active.length} / 10`;
  const checked=latestCheck(), current=checked?.is_current;
  const cov=current?checked.coverage:null;
  $('coverage-summary').textContent=active.length?[
    dual('启用','Active')+': '+active.length,
    dual('未建立检查','Uncovered')+': '+active.filter(r=>!r.flow).length,
    dual('已通过','Passed')+': '+(cov?.passed||0),
    dual('已失败','Failed')+': '+(cov?.failed||0),
    dual('暂无法判断／待复查','Unknown / needs recheck')+': '+(cov?.inconclusive??active.filter(r=>r.flow).length),
    dual('已停用','Retired')+': '+requirements.filter(r=>!r.enabled).length
  ].join(' · '):dual('没有可验收要求，不能判为通过。','No active requirements. This cannot pass.');
  $('requirements').innerHTML=requirements.map(req=>`<div class="flow"><div class="flow-title">${esc(req.title)} <small>v${req.revision} · ${esc(req.id.slice(0,8))}</small></div><p>${esc(req.expectation)}</p><p>${req.enabled?(req.flow?(current?(checked.checks||[]).find(c=>c.requirement_id===req.id)?.status==='passed'?dual('本次通过','Passed this run'):(checked.checks||[]).find(c=>c.requirement_id===req.id)?.status==='failed'?dual('本次失败','Failed this run'):dual('暂时无法判断','Inconclusive'):dual('已确认检查，待复查当前版本','Confirmed check; recheck current version')):dual('待实现，尚未建立检查','Pending implementation; no check yet')):dual('已退出本次验收范围：','Out of acceptance scope: ')+esc(req.reason)}</p>${req.flow?`<details><summary>${t('steps')}</summary><ol>${req.flow.steps.map(s=>`<li>${esc(stepText(s))}</li>`).join('')}</ol></details>`:''}<div class="actions">${req.enabled?`<button data-req="${req.id}" data-op="revise">${dual('修改','Edit')}</button>${req.flow?`<button data-req="${req.id}" data-op="rebuild">${dual('重建检查','Rebuild check')}</button>`:''}<button data-req="${req.id}" data-op="retire">${dual('停用','Retire')}</button>`:`<button data-req="${req.id}" data-op="restore">${dual('恢复并复查','Restore and recheck')}</button>`}</div></div>`).join('');
  if(currentDraft){
    $('original-goal').textContent=dual('原始描述：','Original goal: ')+currentDraft.goal;
    const before=currentDraft.before||[];
    $('draft-flows').innerHTML=(currentDraft.requirements||[]).filter(req=>JSON.stringify(req)!==JSON.stringify(before.find(b=>b.id===req.id))).map(req=>{
      const old=before.find(b=>b.id===req.id);
      return `<div class="flow">${old?`<p>${dual('修改前','Before')}: ${esc(old.title)} — ${esc(old.expectation)} (${old.enabled?'active':'retired'})</p>`:''}<strong>${dual('确认后','After')}: ${esc(req.title)}</strong><p>${esc(req.expectation)}</p><p>${req.enabled?dual('启用','Active'):dual('停用原因：','Retirement reason: ')+esc(req.reason)}</p>${req.flow?flowMarkup(req.flow):dual('尚未建立检查；确认后仍显示未完成。','No check yet; approval does not mark this complete.')}</div>`;
    }).join('');
    $('edit-draft').hidden=!currentDraft.requirements.some(r=>!before.some(b=>b.id===r.id));
  }
  if(r){
    const summary=$('result-summary');
    summary.insertAdjacentHTML('beforeend',`<p class="hint">${esc(new Date(r.created*1000).toLocaleString())} · ${dual('要求版本','Contract version')} ${esc(r.contract_id?.slice(0,10)||'—')}</p>`);
    if(!r.can_accept||historyPinned)summary.insertAdjacentHTML('afterbegin',`<p class="notice">${dual('此记录不能授权当前改动。请查看覆盖情况并复查最新版本。','This record does not approve the current change. Review coverage and check the latest version.')}</p>`);
  }
  document.querySelectorAll('[data-req]').forEach(b=>b.disabled=!!state.busy);
  if(disconnected||actionPending)document.querySelectorAll('#workspace button').forEach(b=>b.disabled=true);
};
async function mutation(operations,goal=$('goal').value||'Review business requirement changes'){
  manualDraft=await api(`/${projectId}/requirement-draft`,'POST',{operations,goal,parent:project().contract_id,source_hash:project().current_source_hash});
  currentDraft=manualDraft;render();$('draft-panel').scrollIntoView({block:'nearest'});
}
function openEditor(action,req=null){
  editingAction=action;editingRequirement=req;
  $('editor-title').textContent=action==='retire'?dual('停用要求','Retire requirement'):dual('编辑业务要求','Edit business requirement');
  $('before-intent').textContent=req?dual('修改前：','Before: ')+req.expectation:'';
  $('req-title').value=req?.title||'';$('req-expectation').value=req?.expectation||'';$('req-purpose').value=req?.purpose||'new';$('req-reason').value='';
  ['req-title','req-expectation','req-purpose'].forEach(id=>$(id).disabled=action==='retire');
  $('req-reason').required=action==='retire';$('req-reason').disabled=action!=='retire';
  $('requirement-editor').showModal();
}
$('add-requirement').onclick=()=>openEditor('add');
$('close-editor').onclick=()=>$('requirement-editor').close();
$('requirement-form').onsubmit=e=>{e.preventDefault();act(async()=>{
  const op={action:editingAction};if(editingRequirement)Object.assign(op,{id:editingRequirement.id,revision:editingRequirement.revision});
  if(editingAction==='retire')op.reason=$('req-reason').value;else op.intent={title:$('req-title').value,expectation:$('req-expectation').value,purpose:$('req-purpose').value};
  await mutation([op]);$('requirement-editor').close();
});};
document.addEventListener('click',e=>{const b=e.target.closest('[data-req]');if(!b)return;const req=currentContract.requirements.find(r=>r.id===b.dataset.req);if(['restore','rebuild'].includes(b.dataset.op))act(()=>mutation([{action:b.dataset.op,id:req.id,revision:req.revision}]));else openEditor(b.dataset.op,req);});
$('bind-requirements').onclick=()=>act(async()=>{manualDraft=null;const r=await api(`/${projectId}/prepare`,'POST',{goal:$('goal').value||'Generate checks for approved requirements',language,stage:'bind',requirement_ids:(currentContract.requirements||[]).filter(r=>r.enabled&&!r.flow).map(r=>r.id)});selectedRun=r.id;historyPinned=false;});
$('service-retry').onclick=()=>refresh(true);
$('download').onclick=e=>{if(disconnected)e.preventDefault();};
function draftRow(req={title:'',expectation:'',purpose:'new'}){
  const box=document.createElement('fieldset');box.className='flow';
  box.innerHTML=`<label>${dual('标题','Title')}<input class="draft-title" minlength="3" maxlength="100" required value="${esc(req.title)}"></label><label>${dual('业务预期','Expected behavior')}<textarea class="draft-expectation" minlength="3" maxlength="400" required>${esc(req.expectation)}</textarea></label><label>${dual('类别','Purpose')}<select class="draft-purpose"><option value="preserve" ${req.purpose==='preserve'?'selected':''}>${dual('保留','Preserve')}</option><option value="new" ${req.purpose==='new'?'selected':''}>${dual('新增','New')}</option></select></label><button type="button" class="remove-draft-row">${dual('移除此未确认项','Remove unapproved item')}</button>`;
  box.querySelector('.remove-draft-row').onclick=()=>box.remove();$('draft-fields').append(box);
}
$('edit-draft').onclick=()=>{$('draft-fields').replaceChildren();currentDraft.requirements.filter(r=>!(currentDraft.before||[]).some(b=>b.id===r.id)).forEach(draftRow);$('draft-editor').showModal();};
$('add-draft-row').onclick=()=>draftRow();
$('close-draft-editor').onclick=()=>$('draft-editor').close();
$('draft-edit-form').onsubmit=e=>{e.preventDefault();act(async()=>{const intents=Array.from($('draft-fields').children).map(row=>({title:row.querySelector('.draft-title').value,expectation:row.querySelector('.draft-expectation').value,purpose:row.querySelector('.draft-purpose').value}));await mutation(intents.map(intent=>({action:'add',intent})),currentDraft.goal);$('draft-editor').close();});};
$('cart-sample').onclick=()=>act(async()=>{const p=await api('/sample/cart','POST');projectId=p.id;selectedRun=null;historyPinned=false;currentContract=null;manualDraft=null;goalProject=p.id;$('goal').value=dual('新增 SAVE10 优惠券：数量为 2 时，折后总价 180.00。保留数量调整、数量必须为 1 至 20、总价计算和刷新保存。','Add SAVE10 coupon: quantity 2 costs 180.00 after discount. Preserve quantity changes, validation from 1 to 20, correct totals, and persistence after reload.');localStorage.setItem(goalKey(p.id),$('goal').value);$('connect-details').open=false;});
render();refresh(true);
