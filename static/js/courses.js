/* Courses page: list courses, open a course, show its PDFs. */

const courses = JSON.parse(document.getElementById('courses-data').textContent);

const courseList = document.getElementById('course-list');
const courseDetail = document.getElementById('course-detail');
const detailTitle = document.getElementById('detail-title');
const pdfList = document.getElementById('pdf-list');

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('collapsed');
}

function showCourse(courseId) {
    const course = courses[courseId];
    if (!course) return;

    courseList.style.display = 'none';
    courseDetail.style.display = 'block';
    detailTitle.textContent = course.name;

    pdfList.innerHTML = '';
    (course.pdfs || []).forEach(pdf => {
        const item = document.createElement('div');
        item.className = 'pdf-item';
        const label = document.createElement('span');
        label.textContent = '📄 ' + pdf.title;
        item.appendChild(label);
        pdfList.appendChild(item);
    });
}

function goBack() {
    courseDetail.style.display = 'none';
    courseList.style.display = 'grid';
}