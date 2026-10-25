#!/bin/zsh
# UI 行为验收：Human Intent → UI State → Decision Envelope 一致性
# 用法: ./ui_behavior_check.sh <review.html 路径>
#   或：REVIEW_ARTIFACT=<review.json 路径> ./ui_behavior_check.sh   （先由 artifact 重建 HTML）
#   需要本机可用 playwright-cli。
set -e
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HTML="$1"
if [[ -z "$HTML" && -n "${REVIEW_ARTIFACT:-}" ]]; then
  python3 "$SKILL_DIR/scripts/review_html.py" --artifact "$REVIEW_ARTIFACT" --out /tmp/ui_behavior_review.html >/dev/null
  HTML=/tmp/ui_behavior_review.html
fi
[[ -n "$HTML" ]] || { echo "用法: $0 <review.html> | REVIEW_ARTIFACT=<review.json> $0"; exit 2; }
[[ -f "$HTML" ]] || { echo "review.html 不存在: $HTML"; exit 2; }
DIR="$(cd "$(dirname "$HTML")" && pwd)"; BASE="$(basename "$HTML")"; PORT=8933
python3 -m http.server "$PORT" --directory "$DIR" >/dev/null 2>&1 & SRV=$!
trap 'kill $SRV 2>/dev/null; playwright-cli close >/dev/null 2>&1 || true' EXIT
sleep 1
playwright-cli open "http://127.0.0.1:$PORT/$BASE" >/dev/null 2>&1
OUT=$(playwright-cli run-code 'async page => {
  const fail=[];const log={};
  await page.waitForSelector(".finding-table .ant-table-tbody tr.ant-table-row",{timeout:30000});
  const row=id=>page.locator(".finding-table .ant-table-tbody tr.ant-table-row").filter({hasText:String(id)});
  const readEnvelope=async()=>{await page.locator(".header-actions .ant-btn-primary").click();await page.waitForSelector(".ant-modal .handoff-text",{timeout:8000});const t=await page.evaluate(()=>document.querySelector(".ant-modal .handoff-text").value);await page.locator(".ant-modal:visible .ant-modal-footer button").first().click();await page.waitForTimeout(500);return JSON.parse(t);};
  const pick=await page.evaluate(()=>{const rows=[...document.querySelectorAll(".finding-table .ant-table-tbody tr.ant-table-row")];let approvable=null,rejectable=null;
    for(const tr of rows){const id=tr.querySelector("td").textContent.replace(/[^0-9]/g,"");const bs=[...tr.querySelectorAll("button")];
      if(!approvable&&bs.some(b=>b.textContent.trim()==="批准"&&!b.disabled))approvable=id;
      if(!rejectable&&bs.some(b=>b.textContent.trim()==="退回重评"))rejectable=id;}
    return {approvable,rejectable};});
  log.pick=pick;
  // ===== A: 批准→取消批准→Envelope 不再授权 =====
  const idA=pick.approvable;
  if(!idA)fail.push("A: 找不到可批准行");else{
    await row(idA).locator("button",{hasText:"批准",exact:true}).click();await page.waitForTimeout(400);
    const tagA=await row(idA).evaluate(tr=>tr.querySelectorAll("td")[4].textContent.trim());
    if(tagA!=="批准")fail.push("A: 批准后 UI 标签="+tagA);
    await row(idA).locator("button",{hasText:"取消批准"}).click();await page.waitForTimeout(400);
    const envA=await readEnvelope();const dA=envA.decisions.find(d=>String(d.findingId)===String(idA));
    if(!dA||dA.status!=="UNDECIDED")fail.push("A: Envelope status="+(dA&&dA.status));
    else log.A="取消批准后 Envelope=UNDECIDED ✓";}
  // ===== C: 退回重评→Envelope=PROVIDE_INFO+理由，不授权 =====
  const idC=pick.rejectable;
  if(!idC)fail.push("C: 找不到退回重评行");else{
    const reason="UI-BEHAVIOR-TEST-"+Date.now();
    await row(idC).locator("button",{hasText:"退回重评"}).click();await page.waitForTimeout(400);
    await page.locator(".ant-modal:visible textarea").fill(reason);
    await page.locator(".ant-modal:visible .ant-btn-primary").click();await page.waitForTimeout(500);
    const tagC=await row(idC).evaluate(tr=>tr.querySelectorAll("td")[4].textContent.trim());
    if(tagC!=="退回重评")fail.push("C: UI 标签="+tagC);
    const envC=await readEnvelope();const dC=envC.decisions.find(d=>String(d.findingId)===String(idC));
    if(!dC||dC.status!=="PROVIDE_INFO")fail.push("C: Envelope status="+(dC&&dC.status));
    else if(dC.note!==reason)fail.push("C: 理由未进 Envelope");
    else if("requiresHumanAcceptance" in dC)fail.push("C: 非 APPROVE 却带验收字段");
    else log.C="退回重评 Envelope=PROVIDE_INFO+note，未授权 ✓";}
  // ===== B: 恢复 AI 默认→Envelope==默认分布，预览计数一致 =====
  await page.locator(".header-actions button",{hasText:"恢复 AI 默认决策"}).click();await page.waitForTimeout(400);
  const desc=await page.evaluate(()=>document.querySelector(".ant-popconfirm-description")?.textContent||"");
  log.resetDesc=desc.slice(0,120);
  await page.locator(".ant-popconfirm .ant-btn-dangerous").click();await page.waitForTimeout(500);
  const envB=await readEnvelope();
  const expect=await page.evaluate(()=>{const r=JSON.parse(document.getElementById("review-data").textContent);
    return Object.fromEntries(r.findings.map(f=>{const a=f.analysis,p=a.proposal;
      const exec=!!(p&&p.summary&&p.approach&&Array.isArray(p.files)&&p.files.length&&Array.isArray(p.verification)&&p.verification.length&&["high","medium","low"].includes(p.fixRisk));
      const def=(a.recommendation==="FIX"&&exec)?"APPROVE":["DISMISS","DEFER"].includes(a.recommendation)?"CLOSE":"UNDECIDED";return [String(f.id),def];}));});
  for(const d of envB.decisions){if(d.status!==expect[String(d.findingId)])fail.push("B: "+d.findingId+" env="+d.status+" 期望默认="+expect[String(d.findingId)]);
    if(d.status==="APPROVE"){
      const expectedAcceptance=await page.evaluate(id=>{const r=JSON.parse(document.getElementById("review-data").textContent);return r.findings.find(f=>f.id===id).analysis.proposal.requiresHumanAcceptance!==false;},d.findingId);
      if(d.requiresHumanAcceptance!==expectedAcceptance)fail.push("B: "+d.findingId+" 验收字段与方案不一致");}}
  const nApprove=envB.decisions.filter(d=>d.status==="APPROVE").length;
  const m=desc.match(/(\d+) 条将随交接执行/);
  if(!m||+m[1]!==nApprove)fail.push("B: 确认框预览计数("+(m&&m[1])+")≠Envelope APPROVE 数("+nApprove+")");
  else log.B="恢复默认后 Envelope==AI 默认分布，预览计数="+m[1]+" ✓";
  return JSON.stringify({verdict:fail.length?"FAIL":"ALL PASS",fail,log});
}' 2>&1)
echo "$OUT" | grep -A1 '^### Result' | tail -1 | python3 -c 'import sys,json;print(json.loads(sys.stdin.read()))' 2>/dev/null || true
if echo "$OUT" | grep -q '"verdict\\":\\"ALL PASS\|"verdict":"ALL PASS'; then echo "✅ UI 行为验收：ALL PASS"; exit 0; else echo "❌ UI 行为验收存在失败"; exit 1; fi
