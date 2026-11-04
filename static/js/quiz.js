let originalQuiz = [];
let quiz = [];
let answers = [];
let current = 0;
const IS_PROFESSOR = true; // no roles yet; change later

const $ = id => document.getElementById(id);


function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

async function loadQuiz() {
  try {
    const res = await fetch("/quiz_data");
    if (!res.ok) throw new Error();
    originalQuiz = await res.json();
  } catch {
    $("quiz-question").textContent = "No quiz available yet.";
    $("quiz-controls").hidden = true;
    return;
  }
  startQuiz();
}

function startQuiz() {
  // Questions the material does not cover have no options, so skip them
  quiz = originalQuiz.filter(q => q.found_in_source !== false && q.options?.length);
  answers = new Array(quiz.length).fill(null);
  current = 0;
  $("quiz-card").hidden = false;
  $("quiz-controls").hidden = false;
  $("quiz-result").hidden = true;
  render();
}

function render() {
  const q = quiz[current];
  const picked = answers[current];

  $("quiz-progress").textContent = `Question ${current + 1} of ${quiz.length}`;
  $("quiz-progress-fill").style.width = `${((current + 1) / quiz.length) * 100}%`;
  $("quiz-question").textContent = q.question;

  const box = $("quiz-answers");
  box.innerHTML = "";
  q.options.forEach((opt, i) => {
    const el = document.createElement("button");
    el.className = "quiz-answer-box";
    el.textContent = opt;
    if (picked !== null) {
      el.disabled = true;
      if (i === q.answer_index) el.classList.add("correct");
      else if (i === picked) el.classList.add("wrong");
    } else {
      el.onclick = () => choose(i);
    }
    box.appendChild(el);
  });

  const expl = $("quiz-explanation");
  expl.textContent = q.explanation || "";
  expl.hidden = picked === null || !q.explanation;

  $("quiz-prev").disabled = current === 0;
  $("quiz-next").disabled = current === quiz.length - 1;

  // Evidence last, so a problem here cannot stop the buttons from updating
  try {
    const evBox = $("quiz-evidence");
    if (evBox && picked !== null) renderProfessorEvidence(q, evBox);
    else if (evBox) evBox.hidden = true;
  } catch (err) {
    console.error("Evidence panel failed:", err);
  }
}

function showTranscript(text, maxLines = 12) {
  const lines = text.split("\n");
  const pre = document.createElement("pre");
  pre.className = "evidence-text";
  pre.textContent = lines.slice(0, maxLines).join("\n");
  if (lines.length <= maxLines) return pre;

  const wrap = document.createElement("div");
  const more = document.createElement("button");
  more.type = "button";
  more.textContent = `Show all ${lines.length} lines`;
  more.onclick = () => {
    pre.textContent = text;
    more.remove();
  };
  wrap.append(pre, more);
  return wrap;
}

function renderProfessorEvidence(q, container) {
  if (!container) return;
  container.innerHTML = "";
  if (!IS_PROFESSOR || !q.evidence) {
    container.hidden = true;
    return;
  }

  const row = document.createElement("div");
  row.className = "evidence-row";

  // Slide images, served from slides_img_all/ via /lecture_files/
  for (const img of q.slide_images || []) {
    const fig = document.createElement("figure");
    const pic = document.createElement("img");
    pic.src = `/lecture_files/${img.path}`;
    pic.alt = `Slide ${img.slide}`;
    pic.className = "evidence-slide";
    const cap = document.createElement("figcaption");
    cap.textContent = `Slide ${img.slide}`;
    fig.append(pic, cap);
    row.appendChild(fig);
  }

  // Transcript the professor used for this question
  const tr = document.createElement("div");
  tr.className = "evidence-transcript";
  const label = document.createElement("strong");
  label.textContent = q.transcript_range ? `[${q.transcript_range}]` : "(no transcript cited)";
  tr.appendChild(label);
  if (q.transcript_range) {
    tr.appendChild(showTranscript(q.evidence[q.transcript_range] || "(not found)"));
  }
  row.appendChild(tr);

  container.appendChild(row);
  container.hidden = false;
}



function choose(i) {
  if (answers[current] !== null) return;
  answers[current] = i;
  render();
}

function finish() {
  const correct = answers.filter((a, i) => a === quiz[i].answer_index).length;
  const skipped = answers.filter(a => a === null).length;

  $("quiz-card").hidden = true;
  $("quiz-controls").hidden = true;
  $("quiz-result").hidden = false;
  $("quiz-score").textContent = `${correct} / ${quiz.length}`;
  $("quiz-score-detail").textContent =
    skipped > 0 ? `${skipped} question(s) left unanswered.` : "Well done!";
}

$("quiz-prev").onclick = () => { if (current > 0) { current--; render(); } };
$("quiz-next").onclick = () => {
  if (current < quiz.length - 1) { current++; render(); }
};
$("quiz-end").onclick = finish;
$("quiz-retake").onclick = startQuiz;

loadQuiz();