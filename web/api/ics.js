// 行事曆訂閱端點。使用者用篩選條件產生訂閱網址，加進 Google / Apple 行事曆，
// 之後符合條件的新賽事、報名截止日會自動出現 —— 這是本產品取代推播的做法。
//
//   /api/ics?sport=run,trail&city=臺中&kids=1&type=exp,camp&minq=3000
//
import events from '../data/events.json' with { type: 'json' };

const PROD = 'https://賽事曆.tw';
const SPORT_LABEL = {
  run: '路跑 / 馬拉松', trail: '越野跑', tri: '鐵人三項', bike: '自行車',
  swim: '游泳 / 泳渡', obstacle: '障礙賽', tennis: '網球', badminton: '羽球',
  tabletennis: '桌球', pickleball: '匹克球', hike: '登山健行', surf: '衝浪', dive: '潛水',
};
const KIND_LABEL = { race: '正式賽事', exp: '體驗活動', camp: '營隊課程' };

const esc = (s = '') => String(s)
  .replace(/\\/g, '\\\\').replace(/;/g, '\;').replace(/,/g, '\\,')
  .replace(/\r?\n/g, '\\n');

// ICS 每行不得超過 75 octets，超過需以「CRLF + 空格」折行
function fold(line) {
  const bytes = Buffer.from(line, 'utf8');
  if (bytes.length <= 73) return line;
  const out = [];
  let cur = Buffer.alloc(0);
  for (const ch of [...line]) {
    const b = Buffer.from(ch, 'utf8');
    if (cur.length + b.length > 73) { out.push(cur.toString('utf8')); cur = Buffer.alloc(0); }
    cur = Buffer.concat([cur, b]);
  }
  if (cur.length) out.push(cur.toString('utf8'));
  return out.join('\r\n ');
}

const nextDay = (d) => {
  const dt = new Date(+d.slice(0, 4), +d.slice(4, 6) - 1, +d.slice(6, 8) + 1);
  return `${dt.getFullYear()}${String(dt.getMonth() + 1).padStart(2, '0')}${String(dt.getDate()).padStart(2, '0')}`;
};

function matches(e, q) {
  if (q.sport?.length && !q.sport.includes(e.s)) return false;
  if (q.city?.length && !q.city.includes(e.c)) return false;
  if (q.type?.length && !q.type.includes(e.t)) return false;
  if (q.kids && !e.k) return false;
  if (q.minq && e.s === 'run' && e.q && e.q < q.minq) return false;
  return true;
}

export default function handler(req, res) {
  const url = new URL(req.url, `https://${req.headers.host}`);
  const list = (k) => (url.searchParams.get(k) || '').split(',').map(s => s.trim()).filter(Boolean);
  const q = {
    sport: list('sport').filter(s => s !== 'all'),
    city: list('city').filter(s => s !== 'all'),
    type: list('type'),
    kids: url.searchParams.get('kids') === '1',
    minq: parseInt(url.searchParams.get('minq') || '0', 10) || 0,
  };
  // 常態服務沒有日期，不適合放進行事曆訂閱
  const hit = events.filter(e => !e.sv && e.d && matches(e, q));

  const L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
             'PRODID:-//island-races//TW Race Calendar//ZH-TW',
             'X-WR-CALNAME:島嶼賽事曆', 'X-WR-TIMEZONE:Asia/Taipei',
             'X-WR-CALDESC:台灣戶外賽事與體驗活動'];

  for (const e of hit) {
    const uid = `${e.i}@island-races`;
    const desc = [
      `${SPORT_LABEL[e.s] || e.s}${e.t !== 'race' ? ' · ' + KIND_LABEL[e.t] : ''}`,
      e.g?.length ? `組別：${e.g.join('、')}` : '',
      e.k ? '設有兒童 / 親子組' : '',
      e.a ? `年齡：${e.a}` : '',
      e.f ? `費用：${e.f}` : '',
      e.q ? `名額：${e.q.toLocaleString()} 人` : '',
      e.rc ? `報名截止：${e.rc}` : '',
      e.u ? `報名頁：${e.u}` : '',
      `資料來源：${e.src}`,
    ].filter(Boolean).join('\n');

    L.push('BEGIN:VEVENT', `UID:${uid}`, `DTSTAMP:${new Date().toISOString().replace(/[-:]|\.\d{3}/g, '')}`,
      `DTSTART;VALUE=DATE:${e.d}`, `DTEND;VALUE=DATE:${nextDay(e.d)}`,
      fold(`SUMMARY:${esc(e.n)}`),
      fold(`LOCATION:${esc([e.c, e.l].filter(Boolean).join(' '))}`),
      fold(`DESCRIPTION:${esc(desc)}`),
      e.u ? fold(`URL:${e.u}`) : null,
      `CATEGORIES:${esc(SPORT_LABEL[e.s] || e.s)}`,
      e.r ? 'RRULE:FREQ=MONTHLY;COUNT=6' : null,   // 常態開課：以月為週期提示
      'END:VEVENT');

    // 報名截止當天另立一筆全天提醒
    if (e.rc) {
      const rc = e.rc.replace(/-/g, '');
      L.push('BEGIN:VEVENT', `UID:${uid}-deadline`,
        `DTSTAMP:${new Date().toISOString().replace(/[-:]|\.\d{3}/g, '')}`,
        `DTSTART;VALUE=DATE:${rc}`, `DTEND;VALUE=DATE:${nextDay(rc)}`,
        fold(`SUMMARY:${esc('【報名截止】' + e.n)}`),
        e.u ? fold(`URL:${e.u}`) : null,
        'END:VEVENT');
    }
  }
  L.push('END:VCALENDAR');

  res.setHeader('Content-Type', 'text/calendar; charset=utf-8');
  res.setHeader('Content-Disposition', 'inline; filename="island-races.ics"');
  res.status(200).send(L.filter(Boolean).join('\r\n') + '\r\n');
}
