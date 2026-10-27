let originalQuiz = [];   
let quiz = [];           
let answers = [];        
let current = 0;

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

// Shuffle options while keeping answer_index pointing at the right one
function shuffled(questions) {
  return questions.map(q => {
    const correct = q.options[q.answer_index];
    const options = [...q.options].sort(() => Math.random() - 0.5);
    return { ...q, options, answer_index: options.indexOf(correct) };
  });
}

function startQuiz() {
  quiz = shuffled(originalQuiz);
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
  $("quiz-next").disabled = current === quiz.length -1;
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