'use strict';
const renderWithRequirements=render;
render=function(){
  renderWithRequirements();
  $('brief-preview').textContent=run()?.repair_brief||'';
  $('brief-details').hidden=!run()?.repair_brief;
  const p=project(), demo=!!p?.guided_demo, reqs=currentContract?.requirements||[];
  const coupon=reqs.find(r=>r.enabled&&r.expectation==='Quantity 2 with SAVE10 costs 180.00');
  const r=latestCheck(), latest=r?.is_current;
  const blocked=state.busy||disconnected||actionPending||!!currentDraft;
  $('guided-start').textContent=dual('免密钥完整体验 →','Try the full flow · no API key →');
  $('guided-start').disabled=!!state.busy||disconnected||actionPending;
  $('guided-panel').hidden=!demo;
  if(!demo)return;
  $('guided-title').textContent=dual('体验：新增功能时，旧功能又坏了','Try it: a new feature breaks an old one');
  $('guided-disclosure').textContent=dual('预设要求与脚本改动演示，浏览器会真实执行检查，不调用模型、不产生模型费用。只修改此会话的独立样例副本；每份要求仍需你确认。','Predefined requirements and scripted changes; real browser checks, no model calls or model charges. Only your isolated sample copy changes. You approve each draft.');
  $('guided-future').textContent=dual('1. 添加尚未实现的优惠券要求','1. Add a future coupon requirement');
  $('guided-feature').textContent=dual('2. 实现示例优惠券并引入价格故障','2. Implement sample coupon + inject price bug');
  $('guided-repair').textContent=dual('3. 修复示例价格并复查','3. Restore sample price + recheck');
  $('guided-future').disabled=blocked||!!coupon||!latest||!r?.can_accept;
  $('guided-feature').disabled=blocked||!coupon||!!coupon.flow;
  $('guided-repair').disabled=blocked||p.demo_stage!=='fault'||!coupon?.flow||!latest||r?.state!=='failed';
  let message;
  if(currentDraft)message=dual('下一步：向下查看预设要求与步骤，点击“确认要求并检查当前版本”。','Next: review the preset requirements and steps below, then confirm and check.');
  else if(state.busy)message=dual('真实浏览器正在检查，请等待结果。','Real browser checks are running.');
  else if(!p.contract_id)message=dual('点击左侧“免密钥完整体验”重新打开待确认草稿。','Use the guided demo button to reopen the baseline draft.');
  else if(!latest)message=dual('请先检查当前改动，以获得当前版本的结果。','Check the current change to get a result for this version.');
  else if(!coupon)message=dual('基线通过后，添加一个尚不存在的优惠券要求，看看系统会不会误报全部通过。','After the baseline passes, add a coupon requirement whose control does not yet exist.');
  else if(!coupon.flow)message=dual('旧要求即使全通过，未覆盖的优惠券仍使结果为未完成。下一步可实现示例功能并故意改坏价格。','Even when old checks pass, the uncovered coupon keeps acceptance incomplete. Next, implement the sample feature and deliberately break its price.');
  else if(p.demo_stage==='fault')message=dual('检查失败后，查看金额差异、截图和“复制给编程 AI”的完整证据，再修复示例价格。','After the check fails, inspect expected/actual totals, screenshots and the complete coding-AI brief, then restore the sample price.');
  else message=dual('体验完成：要求被保留，错误被发现，修复后重新验收。真实项目可在左侧连接；AI 规划需要服务端配置模型。','Walkthrough complete: requirements persisted, the regression was detected and the fix was rechecked. Connect a real project on the left; AI planning needs a configured server-side model.');
  $('guided-next').textContent=message;
};
function useDemoResponse(value){
  manualDraft=value.draft||null;currentDraft=manualDraft;
  if(value.run)selectedRun=value.run.id;
  historyPinned=false;
}
$('guided-start').onclick=()=>act(async()=>{
  const value=await api('/guided-demo','POST');
  projectId=value.project.id;selectedRun=null;currentContract=null;
  useDemoResponse(value);goalProject=projectId;
  $('goal').value=dual('新增 SAVE10 优惠券，同时守住数量校验、总价和刷新保存。','Add SAVE10 coupon while preserving quantity validation, totals and persistence.');
  localStorage.setItem(goalKey(projectId),$('goal').value);$('connect-details').open=false;
});
for(const action of ['future','feature','repair'])$('guided-'+action).onclick=()=>act(async()=>{
  useDemoResponse(await api(`/${projectId}/guided-demo`,'POST',{action,source_hash:project().current_source_hash,contract_id:project().contract_id}));
});
render();
