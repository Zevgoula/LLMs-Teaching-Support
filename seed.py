from db import connect, init_db

COURSES_DATA = [
    # 1st Semester (Winter)
    ("ECE_Y101", "2", "Λογισμός συναρτήσεων μιας μεταβλητής", "6 ECTS", "1"),
    ("ECE_Y104", "3", "Γραμμική Άλγεβρα", "3 ECTS", "1"),
    ("ECE_Y106", "4", "Εισαγωγή στους Υπολογιστές", "6 ECTS", "1"),
    ("ECE_Y107", "5", "Σύγχρονη Φυσική", "4 ECTS", "1"),
    ("ECE_Y108", "5", "Εφαρμοσμένη Φυσική", "4 ECTS", "1"),
    ("ECE_Y109", "6", "Ψηφιακή Λογική", "4 ECTS", "1"),
    
    # 2nd Semester (Summer)
    ("ECE_Y211", "11", "Ηλεκτρικά Κυκλώματα Ι", "5 ECTS", "2"),
    ("ECE_Y212", "2", "Λογισμός Συναρτήσεων πολλών μεταβλητών και Διανυσματική Ανάλυση", "5 ECTS", "2"),
    ("ECE_Y213", "5", "Εργαστήριο Εφαρμοσμένης Φυσικής", "3 ECTS", "2"),
    ("ECE_Y214", "12", "Συνήθεις Διαφορικές Εξισώσεις και Μιγαδικές Συναρτήσεις", "4 ECTS", "2"),
    ("ECE_Y215", "13", "Διαδικαστικός Προγραμματισμός", "6 ECTS", "2"),
    ("ECE_Y210", "14", "Εισαγωγή στην Επιστήμη του Ηλεκτρολόγου Μηχανικού και Τεχνολογίας Υπολογιστών", "3 ECTS", "2"),
]


def seed_courses():
    init_db()
    with connect() as conn:
        # Unpack all 5 values from each tuple
        for code, teacher_id, course_name, description, semester in COURSES_DATA:
            full_course_name = f"{code} {course_name}"
            
            conn.execute(
                """
                INSERT OR IGNORE INTO courses (teacher_id, name, description, semester)
                VALUES (?, ?, ?, ?)
                """,
                (int(teacher_id), full_course_name, description, semester),
            )
    print("Courses seeded successfully!")


if __name__ == "__main__":
    seed_courses()