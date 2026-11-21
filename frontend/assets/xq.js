/* ============ 星桥 · 共享脚本：数据层 / 组件 / 无障碍 ============ */
(function(){
"use strict";
const XQ = window.XQ = {};

/* ---------- 图标库（内联 SVG，离线可用） ---------- */
const P = (d, extra) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra||''}>${d}</svg>`;
XQ.icons = {
  home: P('<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9.5 21v-6h5v6"/>'),
  chat: P('<path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 8.9 8.9 0 0 1-3.8-.8L3 21l1.9-5.2A8.4 8.4 0 1 1 21 11.5z"/><path d="M8.5 10.5h7M8.5 14h4"/>'),
  heart: P('<path d="M12 20.5s-7.5-4.7-9.3-9A5.3 5.3 0 0 1 12 6.6a5.3 5.3 0 0 1 9.3 4.8c-1.8 4.4-9.3 9.1-9.3 9.1z"/>'),
  cards: P('<rect x="3" y="6.5" width="13" height="15" rx="2.5"/><path d="M8 3.5h10.5A2.5 2.5 0 0 1 21 6v12"/><path d="M6.5 11h6M6.5 14.5h6M6.5 18h3.5"/>'),
  chart: P('<path d="M4 20V4"/><path d="M4 20h16"/><path d="M8.5 16v-5M13 16V7.5M17.5 16v-3"/>'),
  arrowR: P('<path d="M4 12h15"/><path d="m13 6 6 6-6 6"/>'),
  arrowL: P('<path d="M20 12H5"/><path d="m11 6-6 6 6 6"/>'),
  check: P('<path d="m4.5 12.5 5 5 10-11"/>'),
  x: P('<path d="M6 6l12 12M18 6 6 18"/>'),
  undo: P('<path d="M4 9h11a5.5 5.5 0 0 1 0 11h-4"/><path d="m8 5-4 4 4 4"/>'),
  download: P('<path d="M12 3v12"/><path d="m7 10.5 5 5 5-5"/><path d="M4 20h16"/>'),
  print: P('<path d="M7 8V3h10v5"/><rect x="3.5" y="8" width="17" height="9" rx="2"/><path d="M7 14h10v7H7z"/>'),
  search: P('<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/>'),
  plus: P('<path d="M12 5v14M5 12h14"/>'),
  trash: P('<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6.5 7 7.5 21h9L17.5 7"/><path d="M10 11v6M14 11v6"/>'),
  eye: P('<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>'),
  bulb: P('<path d="M9 18h6"/><path d="M10 21h4"/><path d="M12 3a6.5 6.5 0 0 0-4 11.6c.8.7 1.3 1.5 1.5 2.4h5c.2-.9.7-1.7 1.5-2.4A6.5 6.5 0 0 0 12 3z"/>'),
  phone: P('<path d="M5 3.5h4l1.5 5-2.5 1.5a12 12 0 0 0 6 6L15.5 13.5l5 1.5v4a2 2 0 0 1-2.2 2A17.5 17.5 0 0 1 3 5.7 2 2 0 0 1 5 3.5z"/>'),
  book: P('<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M8.5 6.5h7M8.5 10h5"/>'),
  tray: P('<path d="M3 13h18"/><path d="M5 13a7 7 0 0 1 14 0"/><path d="M4 17h16"/><path d="M12 6V4"/>'),
  hand: P('<path d="M8 11V5.5a1.5 1.5 0 0 1 3 0V11"/><path d="M11 10.5V4.5a1.5 1.5 0 0 1 3 0V11"/><path d="M14 10.5v-4a1.5 1.5 0 0 1 3 0V14a7 7 0 0 1-7 7h-.8a6 6 0 0 1-4.7-2.3L3 15.5a1.6 1.6 0 0 1 2.4-2L8 16"/>'),
  users: P('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 5a3.5 3.5 0 0 1 0 7"/><path d="M17.5 14.5a6.5 6.5 0 0 1 4 5.5"/>'),
  door: P('<path d="M13 3H5v18h8"/><path d="M13 3l6 2v14l-6 2z"/><circle cx="15.8" cy="12" r=".9" fill="currentColor"/>'),
  clock: P('<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/>'),
  star: P('<path d="m12 3 2.7 5.6 6.1.8-4.5 4.3 1.1 6.1L12 17l-5.4 2.8 1.1-6.1L3.2 9.4l6.1-.8z"/>'),
  play: P('<path d="M7 4.5v15l12-7.5z"/>'),
  refresh: P('<path d="M20 11a8 8 0 1 0-2.3 6.3"/><path d="M20 4.5V11h-6.5"/>'),
  pause: P('<path d="M9 5v14M15 5v14"/>'),
  exit: P('<path d="M14 4h5v16h-5"/><path d="M10 8l-4 4 4 4"/><path d="M6 12h9"/>'),
  filter: P('<path d="M3.5 5h17l-6.5 8v6l-4 2v-8z"/>'),
  info: P('<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><circle cx="12" cy="7.8" r=".9" fill="currentColor"/>'),
  shield: P('<path d="M12 3 5 5.5v6c0 4.5 3 7.7 7 9.5 4-1.8 7-5 7-9.5v-6z"/><path d="m9 12 2 2 4-4.5"/>'),
  sparkle: P('<path d="M12 3.5 13.8 9l5.7 1.8-5.7 1.8L12 18.5l-1.8-5.9L4.5 10.8 10.2 9z"/><path d="M19 16.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/>'),
  calendar: P('<rect x="3.5" y="5" width="17" height="16" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>'),
  send: P('<path d="M21 3 10.5 13.5"/><path d="M21 3 14 21l-3.5-7.5L3 10z"/>'),
  type: P('<path d="M4 7V5h16v2"/><path d="M12 5v14"/><path d="M9 19h6"/>'),
  contrast: P('<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17a8.5 8.5 0 0 0 0-17z" fill="currentColor"/>'),
  moon: P('<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>'),
  flag: P('<path d="M5 21V4"/><path d="M5 4.5h13l-2.5 4 2.5 4H5"/>'),
  pencil: P('<path d="m4 20 1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19z"/><path d="m14.5 6.5 3 3"/>'),
  target: P('<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>'),
  leaf: P('<path d="M4 20C4 10 10 4 20 4c0 10-6 16-16 16z"/><path d="M4 20c4-6 8-9 12-11"/>'),
};
XQ.icon = (n) => XQ.icons[n] || '';
XQ.logoSVG = `<svg viewBox="0 0 48 48" aria-hidden="true">
  <defs><linearGradient id="xq-lg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="var(--apricot)"/><stop offset="1" stop-color="var(--terra)"/></linearGradient></defs>
  <path d="M6 34c4-12 12-18 18-18s14 6 18 18" fill="none" stroke="url(#xq-lg)" stroke-width="3.4" stroke-linecap="round"/>
  <path d="M4 34h40" stroke="var(--honey)" stroke-width="3" stroke-linecap="round"/>
  <path d="M12 34v6M24 22v12M36 34v6" stroke="var(--line-2)" stroke-width="2.4" stroke-linecap="round"/>
  <path d="m24 4 2.2 4.6 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5-3.6-3.5 5-.7z" fill="var(--honey)" stroke="var(--terra-deep)" stroke-width="1.1" stroke-linejoin="round"/>
</svg>`;

/* ---------- 场景与情绪元数据 ---------- */
XQ.SCENES = [
  {id:'directions',   title:'向路人问去书店的路', short:'问路',   icon:'flag',  color:'var(--apricot)', deep:'var(--terra-deep)'},
  {id:'rejected', title:'被拒绝之后怎么回应',     short:'被拒绝后', icon:'door',  color:'var(--rose)',    deep:'var(--rose-deep)'},
  {id:'apologize',title:'在食堂不小心撞到别人',   short:'食堂道歉', icon:'tray',  color:'var(--honey)',   deep:'#7A5A12'},
  {id:'question', title:'课堂上向老师提问',       short:'课堂提问', icon:'hand',  color:'var(--sky)',     deep:'var(--sky-deep)'},
  {id:'join',     title:'加入同学的聊天',         short:'加入聊天', icon:'users', color:'var(--sage)',    deep:'var(--sage-deep)'},
  {id:'call',     title:'打电话向老师请假',       short:'电话请假', icon:'phone', color:'var(--lilac)',   deep:'var(--lilac-deep)'},
  {id:'explain',  title:'别人误解自闭症时，试着解释', short:'解释误解', icon:'chat', color:'var(--sky)', deep:'var(--sky-deep)'},
];
XQ.scene = id => XQ.SCENES.find(s=>s.id===id) || XQ.SCENES[0];
XQ.MOODS = [
  {v:1,label:'很不安',  color:'var(--rose)',   soft:'var(--rose-soft)'},
  {v:2,label:'有点不安',color:'var(--apricot)',soft:'var(--apricot-soft)'},
  {v:3,label:'还好',    color:'var(--honey)',  soft:'var(--honey-soft)'},
  {v:4,label:'比较平静',color:'var(--sage)',   soft:'var(--sage-soft)'},
  {v:5,label:'很平静',  color:'var(--sage-deep)',soft:'var(--sage-soft)'},
];
XQ.mood = v => XQ.MOODS[Math.max(0,Math.min(4,Math.round((v||3)-1)))];
XQ.faceSVG = function(v){
  const m = XQ.mood(v);
  const eyes = v===5
    ? '<path d="M14 19c1.2-1.6 3.4-1.6 4.6 0M25.4 19c1.2-1.6 3.4-1.6 4.6 0" stroke="var(--ink)" stroke-width="2" fill="none" stroke-linecap="round"/>'
    : '<circle cx="16.2" cy="19" r="1.9" fill="var(--ink)"/><circle cx="27.8" cy="19" r="1.9" fill="var(--ink)"/>';
  const brow = v<=2 ? '<path d="M13 13.6l5 1.6M31 13.6l-5 1.6" stroke="var(--ink)" stroke-width="1.8" stroke-linecap="round"/>' : '';
  const mouth = {
    1:'<path d="M16 30c2.4-2.6 5-2.6 8 0" stroke="var(--ink)" stroke-width="2.2" fill="none" stroke-linecap="round" transform="rotate(180 20 29)"/>',
    2:'<path d="M16.5 29.5c2.2-1.6 4.8-1.6 7 0" stroke="var(--ink)" stroke-width="2.2" fill="none" stroke-linecap="round" transform="rotate(180 20 29)"/>',
    3:'<path d="M16.5 28.5h7" stroke="var(--ink)" stroke-width="2.2" stroke-linecap="round"/>',
    4:'<path d="M16 27.5c2.4 2.4 5.6 2.4 8 0" stroke="var(--ink)" stroke-width="2.2" fill="none" stroke-linecap="round"/>',
    5:'<path d="M15.5 27c2.8 3.2 6.2 3.2 9 0" stroke="var(--ink)" stroke-width="2.2" fill="none" stroke-linecap="round"/>',
  }[v] || '';
  const blush = v>=4 ? '<circle cx="11.5" cy="24.5" r="2.4" fill="var(--rose)" opacity=".28"/><circle cx="32.5" cy="24.5" r="2.4" fill="var(--rose)" opacity=".28"/>' : '';
  return `<svg viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="19" fill="${m.soft}" stroke="${m.color}" stroke-width="2"/>${brow}${eyes}${mouth}${blush}</svg>`;
};
XQ.moodInline = v => `<span class="mood-inline">${XQ.faceSVG(v)}${XQ.mood(v).label}</span>`;

/* ---------- 工具 ---------- */
XQ.uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2,7);
XQ.esc = s => String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pad = n => String(n).padStart(2,'0');
XQ.fmtDT = ts => { const d=new Date(ts); return `${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`; };
XQ.fmtD  = ts => { const d=new Date(ts); return `${d.getMonth()+1}月${d.getDate()}日`; };
XQ.dayKey = ts => { const d=new Date(ts); return `${pad(d.getMonth()+1)}-${pad(d.getDate())}`; };
XQ.weekAgo = ts => Date.now()-ts < 7*864e5;
XQ.fmtSecs = s => s<60 ? `${s}秒` : `${Math.floor(s/60)}分${pad(s%60)}秒`;
XQ.downloadCSV = function(name, rows){
  const q = v => `"${String(v==null?'':v).replace(/"/g,'""')}"`;
  const csv = '\uFEFF' + rows.map(r=>r.map(q).join(',')).join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  a.download = name; document.body.appendChild(a); a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href); a.remove();},400);
};

/* ---------- 数据层（localStorage，合成数据种子） ---------- */
const KEY='xq.store.v1';
function lcg(seed){ let s=seed>>>0; return ()=> (s=(s*1664525+1013904223)>>>0)/4294967296; }
const SAY_POOL = {
  directions:{ok:['阿姨您好，打扰一下，请问最近的书店怎么走？','路口左转，经过奶茶店和菜市场再直走，对吗？','谢谢阿姨，我记住了，路上注意车。'],
          warn:['喂，书店在哪？','就那个书店。','（站在那里，等她先开口）']},
  rejected:{ok:['那明天可以借我吗？','好，第一节下课我来找你。谢谢。','没关系，我再问问别人。'],
          warn:['为什么别人可以借你就不行？','好吧。（之后不理他）','你故意的吧。']},
  apologize:{ok:['对不起，撞到你了。我帮你拿纸巾。','纸巾给你，要不要去擦一下？','抱歉，我没注意到后面有人。'],
          warn:['（装作没发生，走开）','我不是故意的。','对不起对不起对不起……']},
  question:{ok:['老师，这一步我没听懂，能再讲一遍吗？','谢谢老师，我明白了。','老师，我想确认一下作业是第几题。'],
          warn:['（一直举手不说话）','这题你讲错了。','（不问，课后抄别人的）']},
  join:{ok:['你们在聊什么？听起来很有意思。','食堂新出的炸鸡排，我也想试试。','明天中午一起去，可以吗？'],
          warn:['（直接坐下，一直盯着看）','你们聊的都没意思。','（插话：我跟你们说我的事……）']},
  call:{ok:['老师您好，我是小明。我发烧了，想请一天假。','好的，谢谢老师，老师再见。','我明天把作业补交给您。'],
          warn:['喂。（不说话）','我不来上学了。','（没等老师说完就挂断）']},
  explain:{ok:['不是你的问题，是我戴着耳机没听见。','教室太吵，我需要缓一下，不是不想理你。','你下次拍我一下，我就知道了。'],
          warn:['（低头不说话）','我又没做错什么。','（摘下耳机走开）']},
};
function seedStore(){
  const rnd = lcg(20261121);
  const pick = arr => arr[Math.floor(rnd()*arr.length)];
  const now = Date.now();
  const at = (daysAgo,h,m) => { const d=new Date(now-daysAgo*864e5); d.setHours(h,m,0,0); return d.getTime(); };
  const sessions=[]; const plan=[
    ['directions',12,4],['rejected',11,3],['directions',10,4],['apologize',9,3],['join',8,2],
    ['rejected',7,4],['question',6,3],['join',5,2],['directions',5,4],['apologize',4,4],
    ['join',3,2],['rejected',3,4],['question',2,4],['call',2,3],['join',1,3],
    ['directions',1,5],['rejected',0,4],['question',0,4],
  ];
  plan.forEach(([sid,daysAgo,mood],i)=>{
    const hard = sid==='join'||sid==='call';
    const nT = 5; const turns=[];
    for(let t=0;t<nT;t++){
      const ok = rnd() < (hard?0.45:0.72) - (daysAgo>7?-0.12:0);
      const kind = ok?'ok':'warn';
      turns.push({tag:ok?'A':pick(['B','C']), say:pick(SAY_POOL[sid][kind]), kind});
    }
    sessions.push({id:'seed-s'+i, sceneId:sid, ts:at(daysAgo, 16+Math.floor(rnd()*4), Math.floor(rnd()*60)),
      turns, ok:turns.filter(t=>t.kind==='ok').length, warn:turns.filter(t=>t.kind==='warn').length,
      mood, secs:150+Math.floor(rnd()*240), completed:true, source:'合成示例'});
  });
  const quizRuns=[]; const EMOS=['开心','难过','生气','害怕','紧张','尴尬','失望','平静'];
  [[12,14,9,6400,3],[9,12,8,5800,3],[6,14,10,5100,4],[3,10,8,4600,4],[1,14,11,4200,5]].forEach(([d,total,correct,rt,mood],i)=>{
    const items=[];
    for(let k=0;k<total;k++){
      const emo=pick(EMOS); const ok = k<correct;
      items.push({emotion:emo, choice: ok?emo:pick(EMOS.filter(e=>e!==emo)), correct:ok, rtMs:rt+Math.floor(rnd()*2600)-1300});
    }
    quizRuns.push({id:'seed-q'+i, ts:at(d,17+Math.floor(rnd()*3),Math.floor(rnd()*60)), total, correct,
      avgRt:Math.round(items.reduce((a,b)=>a+b.rtMs,0)/total), items, mood, source:'合成示例'});
  });
  const tasks=[
    {id:'seed-t1', sceneId:'apologize', title:'本周在食堂，向一位同学说一句礼貌的话', note:'可以是借过、谢谢或对不起。说出一句就算完成，不用长谈。', issuedAt:at(10,9,0), due:at(3,20,0), status:'done',
      checkins:[{ts:at(6,12,40), note:'打饭时跟前面的同学说了「你先请」，他笑了一下。', mood:4}], source:'合成示例'},
    {id:'seed-t2', sceneId:'directions', title:'向路人问一次路（去书店、公交站都行）', note:'用练习过的开头：先打招呼、说清去哪，再复述一遍路线确认。没问清也算完成打卡。', issuedAt:at(9,9,0), due:at(2,20,0), status:'done',
      checkins:[{ts:at(4,16,20), note:'问了去公交站的路，还复述了一遍，对方说“对，就这么走”。', mood:5}], source:'合成示例'},
    {id:'seed-t3', sceneId:'join', title:'课间向正在聊天的同学说一句话', note:'先听一会儿，再问「你们在聊什么」，比如聊食堂新出的炸鸡排。不要求加入整段聊天。', issuedAt:at(5,9,0), due:at(-2,20,0), status:'active', checkins:[], source:'合成示例'},
    {id:'seed-t4', sceneId:'question', title:'这周在课堂上向老师提一个问题', note:'提前把问题写在纸上，举手后照着念也可以。', issuedAt:at(4,9,0), due:at(-3,20,0), status:'active', checkins:[], source:'合成示例'},
    {id:'seed-t5', sceneId:'call', title:'给家人打一个电话，说清一件事', note:'先在心里排好顺序：我是谁、什么事、需要对方做什么。', issuedAt:at(2,9,0), due:at(-5,20,0), status:'active', checkins:[], source:'合成示例'},
    {id:'seed-t6', sceneId:'rejected', title:'如果被拒绝，试着说一句「没关系」', note:'这周遇到任何一次被拒绝都可以打卡，包括线上练习里的。', issuedAt:at(1,9,0), due:at(-6,20,0), status:'active', checkins:[], source:'合成示例'},
    {id:'seed-t7', sceneId:'explain', title:'被误会时，用一句话解释自己', note:'先说“不是你的问题”，再说清自己的情况，最后给一个下次的办法。一句就够。', issuedAt:at(0,9,0), due:at(-6,20,0), status:'active', checkins:[], source:'合成示例'},
  ];
  return {v:1, seededAt:now, sessions, quizRuns, tasks};
}
XQ.get = function(){
  try{
    const raw = localStorage.getItem(KEY);
    if(raw){ const s = JSON.parse(raw); if(s && s.v===1) return s; }
  }catch(e){}
  const s = seedStore();
  try{ localStorage.setItem(KEY, JSON.stringify(s)); }catch(e){}
  return s;
};
XQ.save = s => { try{ localStorage.setItem(KEY, JSON.stringify(s)); }catch(e){} window.dispatchEvent(new CustomEvent('xq-store')); };
XQ.update = fn => { const s=XQ.get(); fn(s); XQ.save(s); return s; };
XQ.onStore = cb => {
  window.addEventListener('xq-store', cb);
  window.addEventListener('storage', e=>{ if(e.key===KEY) cb(); });
};
XQ.events = function(s){
  s = s || XQ.get();
  const ev=[];
  s.sessions.forEach(x=>ev.push({type:'dialogue', ts:x.ts, sceneId:x.sceneId, ref:x,
    label:XQ.scene(x.sceneId).short, detail:`${x.turns.length} 回合 · 完整 ${x.ok} / 需猜测 ${x.warn}`}));
  s.quizRuns.forEach(x=>ev.push({type:'quiz', ts:x.ts, sceneId:null, ref:x,
    label:'情绪情境练习', detail:`${x.total} 题 · 答对 ${x.correct} · 平均 ${(x.avgRt/1000).toFixed(1)} 秒`}));
  s.tasks.forEach(t=>t.checkins.forEach(c=>ev.push({type:'checkin', ts:c.ts, sceneId:t.sceneId, ref:{task:t,checkin:c},
    label:XQ.scene(t.sceneId).short+' · 线下', detail:c.note})));
  return ev.sort((a,b)=>b.ts-a.ts);
};
XQ.onlineCount = (s,sid) => s.sessions.filter(x=>x.sceneId===sid).length;
XQ.offlineCount = (s,sid) => s.tasks.filter(t=>t.sceneId===sid).reduce((a,t)=>a+t.checkins.length,0);

/* ---------- 顶栏 + 无障碍 ---------- */
const NAV=[
  {href:'index.html', label:'首页', icon:'home', page:'home'},
  {href:'展品1-社交脚本对话.html', label:'① 对话练习', icon:'chat', page:'ex1'},
  {href:'展品2-情绪情境练习.html', label:'② 情绪练习', icon:'heart', page:'ex2'},
  {href:'展品3-泛化任务卡.html', label:'③ 任务卡', icon:'cards', page:'ex3'},
  {href:'展品4-学习与情绪记录.html', label:'④ 学习记录', icon:'chart', page:'ex4'},
];
XQ.pref = {
  read(){ try{ return JSON.parse(localStorage.getItem('xq.prefs')||'{}'); }catch(e){ return {}; } },
  write(p){ try{ localStorage.setItem('xq.prefs', JSON.stringify(p)); }catch(e){} }
};
XQ.mountTopbar = function(){
  const host = document.getElementById('topbar');
  if(!host) return;
  const cur = document.body.dataset.page;
  const p = XQ.pref.read();
  host.className='topbar';
  host.innerHTML = `
    <div class="topbar-in">
      <a class="brand" href="index.html">${XQ.logoSVG}
        <span><span class="bt">星桥</span><span class="bs">XINGQIAO</span></span></a>
      <nav class="mainnav" aria-label="页面导航">
        ${NAV.map(n=>`<a href="${n.href}" ${n.page===cur?'aria-current="page"':''}>${n.label}</a>`).join('')}
      </nav>
      <details class="a11y-menu">
        <summary>阅读设置</summary>
        <div class="pop" role="group" aria-label="阅读设置">
          <button type="button" class="a11y-btn" id="xq-motion" aria-pressed="${!!p.motion}">关闭动效</button>
          <button type="button" class="a11y-btn" id="xq-big" aria-pressed="${!!p.big}">大字号</button>
          <button type="button" class="a11y-btn" id="xq-hc" aria-pressed="${!!p.hc}">高对比</button>
        </div>
      </details>
    </div>`;
  const root=document.documentElement;
  const apply=()=>{ root.classList.toggle('no-motion',!!p.motion); root.classList.toggle('big',!!p.big); root.classList.toggle('hc',!!p.hc); };
  apply();
  [['xq-motion','motion'],['xq-big','big'],['xq-hc','hc']].forEach(([id,k])=>{
    document.getElementById(id).addEventListener('click', e=>{
      p[k]=!p[k]; XQ.pref.write(p); apply();
      e.currentTarget.setAttribute('aria-pressed', String(!!p[k]));
    });
  });
};

/* ---------- 提示条（含撤销） ---------- */
XQ.toast = function(msg, opts){
  opts = opts||{};
  let host=document.querySelector('.toasts');
  if(!host){ host=document.createElement('div'); host.className='toasts'; host.setAttribute('aria-live','polite'); document.body.appendChild(host); }
  while(host.children.length>=3) host.firstChild.remove();
  const t=document.createElement('div'); t.className='toast';
  t.innerHTML = `${XQ.icon(opts.icon||'check')}<span>${XQ.esc(msg)}</span>`;
  let timer;
  const dismiss=()=>{ clearTimeout(timer); t.classList.add('out'); setTimeout(()=>t.remove(),260); };
  if(opts.undo){
    const b=document.createElement('button'); b.type='button'; b.className='undo-btn'; b.textContent='撤销';
    b.addEventListener('click',()=>{ opts.undo(); dismiss(); XQ.toast('已撤销',{icon:'undo'}); });
    t.appendChild(b);
  }
  host.appendChild(t);
  timer=setTimeout(dismiss, opts.undo?6500:3200);
  return dismiss;
};

/* ---------- 抽屉 / 模态 ---------- */
function trapFocus(box, e){
  if(e.key!=='Tab') return;
  const f=[...box.querySelectorAll('a[href],button:not(:disabled),input,select,textarea,[tabindex]:not([tabindex="-1"])')].filter(x=>x.offsetParent!==null);
  if(!f.length) return;
  const first=f[0], last=f[f.length-1];
  if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
  else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
}
XQ.drawer = function({title, body, foot}){
  document.querySelectorAll('.xq-drawer,.xq-scrim-d').forEach(n=>n.remove());
  const prev=document.activeElement;
  const scrim=document.createElement('div'); scrim.className='scrim xq-scrim-d open';
  const d=document.createElement('aside'); d.className='drawer xq-drawer open'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true'); d.setAttribute('aria-label',title);
  d.innerHTML=`<div class="drawer-head"><h3>${XQ.esc(title)}</h3>
    <button type="button" class="icon-btn xq-close" aria-label="关闭详情">${XQ.icon('x')}</button></div>
    <div class="drawer-body">${body}</div>${foot?`<div class="drawer-foot">${foot}</div>`:''}`;
  document.body.append(scrim,d);
  const close=()=>{ d.classList.remove('open'); scrim.classList.remove('open');
    setTimeout(()=>{d.remove();scrim.remove();},300);
    document.removeEventListener('keydown',onKey); if(prev&&prev.focus) prev.focus(); };
  const onKey=e=>{ if(e.key==='Escape') close(); trapFocus(d,e); };
  document.addEventListener('keydown',onKey);
  scrim.addEventListener('click',close);
  d.querySelector('.xq-close').addEventListener('click',close);
  d.querySelector('.xq-close').focus();
  return {close, el:d};
};
XQ.modal = function({title, body, foot}){
  document.querySelectorAll('.xq-modal-wrap').forEach(n=>n.remove());
  const prev=document.activeElement;
  const w=document.createElement('div'); w.className='modal-wrap xq-modal-wrap open';
  w.innerHTML=`<div class="modal" role="dialog" aria-modal="true" aria-label="${XQ.esc(title)}">
    <div class="modal-head"><h3>${XQ.esc(title)}</h3>
    <button type="button" class="icon-btn xq-close" aria-label="关闭">${XQ.icon('x')}</button></div>
    <div class="modal-body">${body}</div>${foot?`<div class="modal-foot">${foot}</div>`:''}</div>`;
  document.body.appendChild(w);
  const close=()=>{ w.classList.remove('open'); setTimeout(()=>w.remove(),280);
    document.removeEventListener('keydown',onKey); if(prev&&prev.focus) prev.focus(); };
  const onKey=e=>{ if(e.key==='Escape') close(); trapFocus(w,e); };
  document.addEventListener('keydown',onKey);
  w.addEventListener('click',e=>{ if(e.target===w) close(); });
  w.querySelector('.xq-close').addEventListener('click',close);
  const f=w.querySelector('textarea,input,select,button:not(.xq-close)'); if(f) f.focus();
  return {close, el:w};
};

/* ---------- 情绪量表组件 ---------- */
XQ.moodScale = function(host, onPick, selected){
  host.innerHTML = XQ.MOODS.map(m=>`
    <button type="button" class="mood-btn" data-v="${m.v}" aria-pressed="${selected===m.v}" aria-label="情绪自评：${m.label}">
      ${XQ.faceSVG(m.v)}<span class="ml">${m.label}</span></button>`).join('');
  host.querySelectorAll('.mood-btn').forEach(b=>b.addEventListener('click',()=>{
    host.querySelectorAll('.mood-btn').forEach(x=>x.setAttribute('aria-pressed','false'));
    b.setAttribute('aria-pressed','true');
    onPick(+b.dataset.v);
  }));
};

/* ---------- 图表（SVG，用 CSS 变量以兼容高对比） ---------- */
XQ.ringSVG = function(pct, center, sub){
  const r=46, c=2*Math.PI*r, off=c*(1-Math.max(0,Math.min(1,pct)));
  return `<svg viewBox="0 0 112 112" role="img" aria-label="${XQ.esc(center)} ${XQ.esc(sub||'')}">
    <circle cx="56" cy="56" r="${r}" fill="none" stroke="var(--surface-2)" stroke-width="11"/>
    <circle cx="56" cy="56" r="${r}" fill="none" stroke="var(--sage)" stroke-width="11" stroke-linecap="round"
      stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}" transform="rotate(-90 56 56)"/>
    <text x="56" y="55" text-anchor="middle" class="ring-center">${XQ.esc(center)}</text>
    <text x="56" y="72" text-anchor="middle" class="ring-sub">${XQ.esc(sub||'')}</text></svg>`;
};
XQ.pairBarsSVG = function(rows, opts){
  opts=opts||{};
  const W=660, H=250, padL=40, padB=44, padT=18, padR=12;
  const max=Math.max(4, ...rows.map(r=>Math.max(r.a,r.b)));
  const step=Math.ceil(max/4); const top=step*4;
  const iw=W-padL-padR, ih=H-padT-padB;
  const gw=iw/rows.length, bw=Math.min(30, gw/3.2);
  let g='';
  for(let i=0;i<=4;i++){
    const y=padT+ih-ih*i/4;
    g+=`<line x1="${padL}" y1="${y}" x2="${W-padR}" y2="${y}" stroke="var(--line)" stroke-width="1" ${i===0?'':'stroke-dasharray="3 5"'}/>
        <text x="${padL-8}" y="${y+4}" text-anchor="end" font-size="10" fill="var(--ink-3)">${step*i}</text>`;
  }
  rows.forEach((r,i)=>{
    const cx=padL+gw*i+gw/2;
    const ha=ih*r.a/top, hb=ih*r.b/top;
    g+=`<rect x="${cx-bw-3}" y="${padT+ih-ha}" width="${bw}" height="${Math.max(ha,r.a?2:0)}" rx="5" fill="var(--apricot)"/>
        <rect x="${cx+3}" y="${padT+ih-hb}" width="${bw}" height="${Math.max(hb,r.b?2:0)}" rx="5" fill="var(--sage)"/>
        <text x="${cx-bw/2-3}" y="${padT+ih-ha-5}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--terra-deep)">${r.a}</text>
        <text x="${cx+bw/2+3}" y="${padT+ih-hb-5}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--sage-deep)">${r.b}</text>
        <text x="${cx}" y="${H-padB+18}" text-anchor="middle" font-size="11.5" fill="var(--ink-2)">${XQ.esc(r.label)}</text>`;
  });
  return `<div class="chart-box"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${XQ.esc(opts.aria||'线上练习与线下使用次数对比柱状图')}">${g}</svg>
    <div class="legend"><span><i style="background:var(--apricot)"></i>${XQ.esc(opts.aLabel||'线上练习（次）')}</span>
    <span><i style="background:var(--sage)"></i>${XQ.esc(opts.bLabel||'线下使用（次）')}</span></div></div>`;
};
XQ.lineSVG = function(points, opts){
  opts=opts||{};
  const W=660,H=190,padL=34,padR=14,padT=16,padB=30;
  const iw=W-padL-padR, ih=H-padT-padB;
  const min=1,max=5;
  const x=i=>padL+(points.length<2?iw/2:iw*i/(points.length-1));
  const y=v=>padT+ih-ih*(v-min)/(max-min);
  let grid='';
  for(let v=min;v<=max;v++){
    grid+=`<line x1="${padL}" y1="${y(v)}" x2="${W-padR}" y2="${y(v)}" stroke="var(--line)" stroke-width="1" stroke-dasharray="${v===3?'':'3 5'}"/>
      <text x="${padL-7}" y="${y(v)+4}" text-anchor="end" font-size="9.5" fill="var(--ink-3)">${v}</text>`;
  }
  const path=points.map((p,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
  const area=path+` L${x(points.length-1).toFixed(1)},${padT+ih} L${x(0).toFixed(1)},${padT+ih} Z`;
  const dots=points.map((p,i)=>`<circle cx="${x(i).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="3.6" fill="${XQ.mood(p.v).color}" stroke="var(--surface)" stroke-width="1.6"><title>${XQ.esc(p.label)}：${XQ.mood(p.v).label}</title></circle>`).join('');
  const labels=points.map((p,i)=> (points.length<=8 || i%Math.ceil(points.length/7)===0 || i===points.length-1)
    ? `<text x="${x(i).toFixed(1)}" y="${H-8}" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">${XQ.esc(p.label)}</text>`:'').join('');
  return `<div class="chart-box"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${XQ.esc(opts.aria||'情绪平静度趋势折线图，1 很不安到 5 很平静')}">
    <defs><linearGradient id="xq-mood-g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="var(--honey)" stop-opacity=".38"/><stop offset="1" stop-color="var(--honey)" stop-opacity="0"/></linearGradient></defs>
    ${grid}<path d="${area}" fill="url(#xq-mood-g)"/><path d="${path}" fill="none" stroke="var(--terra)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>${dots}${labels}</svg></div>`;
};
XQ.stackRows = function(rows){
  const max=Math.max(1,...rows.map(r=>r.ok+r.warn));
  return rows.map(r=>{
    const tot=r.ok+r.warn;
    return `<div class="bars-row"><span class="bl">${XQ.esc(r.label)}</span>
      <span class="bar-track" role="img" aria-label="${XQ.esc(r.label)}：信息完整 ${r.ok} 次，需要猜测 ${r.warn} 次">
        <span class="bar-seg" style="width:${(r.ok/max*100).toFixed(1)}%;background:var(--sage)"></span>
        <span class="bar-seg" style="width:${(r.warn/max*100).toFixed(1)}%;background:var(--apricot)"></span>
      </span><span class="bv">${tot}</span></div>`;
  }).join('') + `<div class="legend"><span><i style="background:var(--sage)"></i>信息完整的说法</span>
    <span><i style="background:var(--apricot)"></i>对方需要猜测的说法</span></div>`;
};

/* ---------- 启动 ---------- */
document.addEventListener('DOMContentLoaded', ()=>{ XQ.mountTopbar(); XQ.get(); });
})();