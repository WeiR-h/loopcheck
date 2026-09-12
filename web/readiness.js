'use strict';
let readinessResult=null, readinessAction=null;
const renderWithDemo=render;
render=function(){
  renderWithDemo();
  const p=project(), model=state.model, busy=state.busy||disconnected||actionPending;
  const active=(currentContract?.requirements||[]).filter(r=>r.enabled);
  $('prepare').textContent=dual('生成业务要求','Prepare requirements');
  $('check').classList.toggle('primary',active.length>0);
  $('prepare').classList.toggle('primary',active.length===0);
  $('cart-sample').textContent=dual('购物车开发场景 →','Development sample: Everyday Cart →');
  $('add-requirement').textContent=dual('新增要求','Add requirement');
  $('bind-requirements').textContent=dual('为未覆盖要求生成检查','Generate missing checks');
  $('edit-draft').textContent=dual('编辑业务提案','Edit business proposal');
  $('brief-details').querySelector('summary').textContent=dual('完整复现说明','Full reproduction brief');
  $('live-sample').textContent=dual('真实 AI 规划：购物清单 →','Live AI planning: shopping list →');
  $('live-sample').disabled=!!busy;
  $('model-summary').textContent=model?`${model.model} · `+(model.configured?dual('模型已配置；生成要求和步骤会调用模型，已有检查重跑不调用模型。','Model configured. Planning uses the provider; replaying checks needs no model.') : dual('未配置模型。可使用免密钥体验或重跑已有检查。','No model configured. Try the keyless walkthrough or replay existing checks.')):'';
  $('readiness-check').textContent=dual('检查连接状态','Check readiness');
  $('readiness-check').disabled=!p||!!busy;
  if(p){
    const link=p.preview_url??(state.public?null:p.url);
    $('preview').hidden=!link;
    if(link)$('preview').href=link;
    if(state.public)$('project-address').textContent=dual('随包样例 · 在服务器中验收','Bundled sample · checked on the server');
  }
  if(readinessResult?.project_id!==p?.id)readinessResult=null;
  $('readiness-result').hidden=!readinessResult;
  if(readinessResult){
    const d=readinessResult;
    const sourceCurrent=d.source.version===p.current_source_hash;
    const reasons={unreachable:dual('请先启动项目预览','Start the project preview first'),timeout:dual('预览响应超时，请检查服务','Preview timed out; check the server'),redirect:dual('地址发生跳转，请连接最终本地地址','Preview redirects; connect its final local URL'),http_error:dual('预览返回错误','Preview returned an error')};
    $('readiness-result').textContent=[dual('源码：','Source: ')+(d.source.ready&&sourceCurrent?dual('可读取','readable'):dual('已变化或不可读取，请重新检查','changed or unavailable; check again')),
      dual('预览：','Preview: ')+(d.preview.ready?dual('可访问','reachable'):reasons[d.preview.reason]||d.preview.reason),
      dual('模型预算余额约 ¥','Approx. provider budget remaining ¥')+d.remaining_budget_cny.toFixed(3),
      dual('这是连接状态，不是验收结论；模型可用性以实际调用为准。','Connection status only, not acceptance. Provider availability needs an actual call.')].join(' · ');
  }
  const latest=latestCheck(), uncovered=active.filter(r=>!r.flow).length;
  let message, label, action;
  if(!p){message=dual('先选择一个样例，或连接正在开发的本地项目。','Choose a sample or connect your running local project.');label=dual('体验完整流程','Try the full workflow');action=()=> $('guided-start').click();}
  else if(currentDraft){message=dual('下一步：审阅草稿。只有你确认的要求才会纳入验收。','Next: review the draft. Only approved requirements enter acceptance.');label=dual('查看待确认要求','Review the draft');action=()=> $('draft-panel').scrollIntoView({block:'start',behavior:'smooth'});}
  else if(busy){message=dual('正在处理。结果不会自动修改你的业务要求。','Work is in progress. Your approved expectations remain unchanged.');label=dual('查看执行状态','View progress');action=()=> $('result-summary').scrollIntoView({block:'center'});}
  else if(!active.length){message=dual('下一步：描述必须保留的行为，生成并确认业务要求。','Next: describe what matters, then prepare and approve requirements.');label=dual('填写修改目标','Describe the change');action=()=> $('goal').focus();}
  else if(uncovered){message=dual(`${uncovered} 条启用要求尚无检查。功能实现后，再生成步骤并确认；目前不能判为全部通过。`,`${uncovered} active requirements have no checks. Once implemented, generate and approve steps; acceptance remains incomplete.`);label=dual('为未覆盖要求生成检查','Generate missing checks');action=()=> $('bind-requirements').click();}
  else if(historyPinned){message=dual('下方是历史详情；顶部覆盖情况仍来自最新检查。','The detail below is historical; coverage above comes from the latest check.');label=dual('返回最新结果','View latest result');action=()=>{selectedRun=latest?.id||null;historyPinned=false;render();};}
  else if(latest?.is_current&&latest.state==='failed'){message=dual('先把复现证据交给编程 AI；修复源码后重跑同一组要求。','Send reproduction evidence to your coding AI, then recheck the same requirements after fixing the source.');label=dual('查看完整复现说明','View full reproduction');action=()=>{$('brief-details').open=true;$('brief-details').scrollIntoView({block:'start'});};}
  else{message=latest?.can_accept?dual('当前已确认要求全部通过。继续改码后，重跑这些要求即可。','Current confirmed requirements pass. Replay them after the next code change.'):dual('下一步：检查当前源码，历史通过不能替代当前验收。','Next: check current source. Historical passes do not approve this version.');label=dual('检查当前改动','Check this change');action=()=> $('check').click();}
  $('next-step-panel').hidden=disconnected;
  $('next-step-text').textContent=message;$('next-step').textContent=label;
  $('next-step').disabled=!!busy||(!currentDraft&&uncovered>0&&!model?.configured);
  readinessAction=action;
};
$('next-step').onclick=()=>readinessAction?.();
$('readiness-check').onclick=()=>act(async()=>{readinessResult=await api(`/${projectId}/readiness`);});
$('live-sample').onclick=()=>act(async()=>{
  const p=await api('/sample/public/shopping','POST');
  projectId=p.id;selectedRun=null;historyPinned=false;currentContract=null;manualDraft=null;goalProject=p.id;
  $('goal').value='Add Milk to the shopping list and verify that Milk appears and the input clears. Then delete Milk and verify that the list is empty.';
  localStorage.setItem(goalKey(p.id),$('goal').value);$('connect-details').open=false;
  notice(dual('公开 MDN CC0 样例。下一步点击“生成验收要求”，由真实模型规划；这里没有预设检查脚本。','Public MDN CC0 example. Prepare requirements next for live model planning; this path has no preset check script.'));
});
render();
