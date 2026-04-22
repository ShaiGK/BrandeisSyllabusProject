# Syllabus Annotation Guidelines

**Project:** Brandeis Syllabus Information Extraction  
**Task:** Span-level topic annotation of course syllabi

---

## 1. Project Background and Goals

We are building a dataset of annotated Brandeis University course syllabi. The goal is to label spans of text according to the type of information they contain, using a fixed set of 12 topic categories.

The downstream use case is a retrieval system that can answer common student questions directly from a syllabus — e.g., "What is the late work policy?" or "How do I get disability accommodations?" Your annotations teach a model where in the document to look for each type of information.

Annotations from all team members are merged into a shared file automatically by `annotate.py`. Please read these guidelines carefully before starting, and refer back to them when you encounter edge cases.

---

## 2. How to Annotate

### Setup (one time only)
See the README for full instructions. You need Label Studio running in a separate terminal and your API token configured via `python annotate.py setup`.

### Each annotation session
1. Open a terminal and run: `label-studio start`
2. In a second terminal, run: `python annotate.py start`
3. Your browser will open to a batch of syllabi. Click **Label All Tasks**.
4. For each syllabus, highlight spans of text and assign labels using the toolbar.
5. Click **Submit** after finishing each document.
6. When done for the session, run: `python annotate.py finish`

### What you are doing
For each syllabus, you will:
- Read through the document
- Highlight every span of text that clearly belongs to one of the 12 label categories
- Assign that span a single label
- Mark the document's validity (see Section 4)
- Optionally add a note if something is unusual

---

## 3. The Annotation Ontology

There are 12 topic labels. Every span you annotate must use exactly one of these.

| Label | Full Name | What it covers |
|---|---|---|
| **ACCOM** | Accommodations | Disability support, accessibility services, how to request accommodations |
| **ATTEND** | Attendance / Participation | Class attendance rules, absence policies, participation expectations |
| **GRADE** | Grading / Evaluation | How the final grade is calculated — weights, grading scale, evaluation criteria |
| **ASSIGN** | Assignments / Requirements | Descriptions of required coursework: homework, projects, exams, deliverables |
| **LATE** | Deadlines / Late Work | Due dates, late penalties, extensions, make-up or incomplete policies |
| **MATERIAL** | Course Materials | Required or recommended textbooks, software, readings, or supplies |
| **INTEGRITY** | Academic Integrity | Plagiarism, cheating, unauthorized collaboration, AI misuse policies |
| **ADMIN** | Administrative Info | Office hours, instructor contact, email policy, course prerequisites, administrative logistics |
| **SCHEDULE** | Course Schedule | Week-by-week topics, reading schedules, course calendars, exam dates |
| **CONDUCT** | Classroom Conduct | Behavioral expectations, device policies, classroom etiquette |
| **DESCRIP** | Course Description | Course overview, learning objectives, goals, what the course is about |
| **CTF** | Capture the Flag | Hidden easter eggs or CTF-style challenges embedded in the syllabus (rare) |

### Label descriptions in detail

**ACCOM** — Any text describing how students with disabilities or special needs can receive support. Typically mentions the university's student accessibility office (at Brandeis: Student Accessibility Support). Includes: documentation requirements, how to submit accommodation requests, what kinds of accommodations are available.

**ATTEND** — Policies about physically or virtually attending class. Includes: how many absences are allowed, consequences of excessive absences, how to notify the instructor of an absence, whether attendance is graded, synchronous vs. asynchronous participation expectations.

**GRADE** — The grading breakdown for the course. Includes: assignment weights (e.g., "Homework 30%, Midterm 30%, Final 40%"), the grading scale (A = 93–100, etc.), curve policies, pass/fail options. **Does not include** descriptions of what the assignments are — that is ASSIGN.

**ASSIGN** — What students are required to do. Includes: descriptions of homework, projects, papers, exams, presentations, labs, and any other deliverables. May include submission instructions (where/how to submit). **Does not include** the grading weight of the assignment — that is GRADE. **Does not include** due dates — that is LATE or SCHEDULE.

**LATE** — Rules about what happens when work is submitted after the deadline. Includes: late penalty amounts (e.g., "10% per day"), extension request policies, whether extensions are available and under what conditions, make-up exam policies, incomplete grade policies.

**MATERIAL** — What students need to obtain for the course. Includes: required textbooks (with author/edition/ISBN), recommended readings, required software or tools, lab materials, course packets. If materials are listed alongside a schedule (e.g., "Week 1: Read Chapter 1"), annotate the schedule as SCHEDULE and annotate a separate materials section as MATERIAL.

**INTEGRITY** — Rules about academic honesty. Includes: definitions of plagiarism, what constitutes cheating, rules about collaboration and group work, AI tool policies **when framed as a restriction or misconduct** (see edge cases), citation requirements, consequences for violations, links to the university honor code.

**ADMIN** — Logistical and contact information that doesn't fit other categories. Includes: instructor and TA names, emails, office hours and locations, how and when to contact the instructor, course meeting times and location, course number/section, prerequisites, credit hours, links to the course LMS. This is a catch-all for administrative logistics that students need to navigate the course.

**SCHEDULE** — A structured timeline of the course. Includes: week-by-week topic lists, reading or assignment schedules tied to specific dates or weeks, exam dates embedded in a calendar view. If a schedule lists readings, annotate the whole schedule block as SCHEDULE — do not try to carve out MATERIAL spans from within it.

**CONDUCT** — Rules about how students should behave in class. Includes: phone and laptop policies, recording policies, expectations around respectful discussion, dress codes (rare), policies on eating in class. Also includes more formal conduct policies like Title IX statements, non-discrimination statements, and harassment policies when they are framed as behavioral expectations.

**DESCRIP** — What the course is about. Includes: the catalog description, the instructor's description of course goals and themes, learning objectives, what topics will be covered, what students will be able to do by the end. This is typically at the top of the syllabus.

**CTF** — Capture-the-flag puzzles or hidden messages that some instructors embed in their syllabi as a fun exercise. These are very rare. If you find one, annotate it. If you're unsure whether something is a CTF, leave it unannotated and add a note.

---

## 4. Document Validity

Before annotating spans, mark the document as a whole using the **Validity** field in Label Studio.

| Validity | When to use |
|---|---|
| **Valid** | The document is a recognizable course syllabus with at least some annotatable content. Use this for the vast majority of documents. |
| **Invalid** | The document is not a syllabus — it is a blank page, a form, a completely garbled PDF extraction, or something clearly uploaded by mistake. |

Most documents should be marked **Valid**. Only mark **Invalid** if the document is truly not a syllabus. A short or incomplete syllabus is still Valid.

Documents marked **Invalid** are automatically excluded from the training data by the conversion script.

---

## 5. What to Annotate

### Annotate all relevant spans
Go through the full document and annotate every span that clearly fits one of the 12 categories. A typical syllabus will have 5–10 annotated spans. Some will have more.

### What counts as a span
A span is a contiguous block of text. It can be:
- A single sentence
- A bullet list (highlight from the first bullet through the last)
- A paragraph or multiple paragraphs
- A full section (heading + body text)

**Spans do not need to align with sentences or paragraphs.** Annotate exactly the text that is relevant — no more, no less.

### Include section headings when they help
If a section has a heading that meaningfully identifies the content, include it in the span. If the heading is generic (e.g., "Policies"), don't bother including it — just annotate the body text.

- **Include:** "Academic Integrity\nAll work must be your own. Plagiarism will result in..."
- **Include:** "Grading\nHomework 40%, Midterm 30%, Final 30%..."
- **Skip heading:** "Other Policies\n[attendance content here]" — just annotate the attendance content

### Annotate coherent blocks together
If a paragraph or bullet list clearly all belongs to one category, annotate it as one span. Don't split it line by line.

---

## 6. What Not to Annotate

- **Generic text that doesn't fit any category.** Not everything in a syllabus needs to be annotated. Course title pages, professor bios, acknowledgements, and filler text are fine to leave unannotated.
- **Titles or headings alone.** Don't annotate "Grading Policy" by itself with no body text unless the heading is genuinely the only content.
- **Very short unclear fragments.** If a sentence is ambiguous and you can't determine its category, skip it.

---

## 7. Span Selection: How Much Text to Include

### Select all text that belongs to the category
If a section of the syllabus is about grading, select the entire grading section — all of it — as one GRADE span. Don't shrink it to a single sentence just because that sentence is the "key" one. On the other hand, don't drag in neighboring text that belongs to a different category or to no category at all.

**Too little:**
> *"Homework is worth 40% of your grade."*  ← left out the rest of the grading breakdown

**Just right:**
> *[Full grading section: the breakdown table, the grading scale, the curve policy — all selected as one GRADE span]*

**Too much:**
> *[Full grading section plus the attendance policy that follows it, all selected as GRADE]*

### You can annotate multiple non-contiguous spans with the same label
A label does not have to appear only once per document. If grading information is discussed in two separate places in the syllabus — say, a brief mention in the course overview and a full breakdown later — create two separate GRADE spans. The spans do not need to be adjacent or contiguous.

**Example of correct multi-span annotation:**
- Span 1 (GRADE): Paragraph near the top that briefly mentions the grade breakdown
- Span 2 (LATE): The late work policy in a separate section
- Span 3 (GRADE): The full grading section later in the document
- Span 4 (LATE): A note at the bottom reminding students of the no-extension rule

### Don't include text that doesn't fit the label
If a section mixes topics, only select the portion that clearly belongs to the label you are assigning. Leave the rest for a separate span or unannotated.

**Example:** A paragraph that opens with course objectives (DESCRIP) and then transitions into the grading breakdown (GRADE) — annotate them as two separate spans with their respective labels, not as one combined span.

### Page numbers embedded in the text
When a syllabus is extracted from a PDF, bare page numbers (e.g., a lone "3" on its own line) often appear in the middle of a section. **Include them inside your span** — do not stop and restart the span around them. These page-number lines are automatically filtered out during data processing, so including them has no effect on the final labels.

**Example:** If a GRADE section runs across pages 4 and 5, select from the first line of the section straight through to the last line, dragging over the "5" that appears between the pages. Do not split it into two separate GRADE spans.

---

## 8. Splitting Spans for Different Categories

If a section of the syllabus covers two different topics, annotate them as two separate spans.

**Example:** A "Policies" section that first describes the grading breakdown and then describes the attendance rules → annotate the grading part as GRADE and the attendance part as ATTEND. They can be adjacent. Overlapping spans should be avoided whenever possible.

**When splitting is impractical:** If two categories are so interleaved (e.g., alternating sentences) that clean separation is impossible, annotate the whole block under the dominant category and add a note.

---

## 9. Edge Cases

### AI tool policies
- AI use **framed as misconduct or a restriction** → **INTEGRITY**  
  *"The use of ChatGPT or other AI tools to complete assignments is considered academic dishonesty."*
- AI use **framed as an allowed or required tool** → **ASSIGN**, **MATERIAL**, **CONDUCT**, etc. (depending on the context)   
  *"You may use AI tools to help brainstorm, but all submitted text must be your own."*
- When a syllabus has a standalone "AI Policy" section that does both, annotate the whole section as **INTEGRITY** (the restriction framing usually dominates).

### Overlapping categories
When text genuinely fits two categories, choose the **dominant purpose**:
- "Homework is due Fridays at 11:59pm. Late homework loses 5% per day." → **LATE** (the due-date/penalty info is the point; the assignment is mentioned only to identify it)
- "Homework must be submitted on Canvas as a PDF. Late submissions are not accepted." → **ASSIGN** for the submission instructions, **LATE** for the no-late-submissions sentence (two separate spans if they're in separate sentences; single ASSIGN span if they're in one sentence and the submission rule is the main point)

### Schedule with embedded assignment descriptions
SCHEDULE takes priority when text is organized as a timeline. If a schedule row says "Week 3: Memory allocation (Reading: Ch. 4; Homework 2 due)", annotate the full schedule block as SCHEDULE — don't try to carve out ASSIGN or LATE spans within it.

### Title IX / non-discrimination statements
Annotate as **CONDUCT** if they are framed as behavioral expectations or classroom norms. If they are simply boilerplate legal disclosures with no direct behavioral content, it is okay to skip them.

### Missing categories
Not every syllabus will contain every category. A short syllabus might have only DESCRIP, GRADE, ASSIGN, and SCHEDULE. That is fine — only annotate what is actually present.

### Very short syllabi
If a syllabus is only one or two paragraphs (common for some courses), annotate whatever you can. Mark it Valid unless it is truly not a syllabus.

---

## 10. Annotation Quality Tips

- **Read the whole document first**, then go back and annotate. This helps you understand structure before committing to span boundaries.
- **Annotate based on meaning, not formatting.** A paragraph with no heading can still clearly be ATTEND. A paragraph under a heading labeled "Policies" could contain anything.
- **When in doubt about boundaries**, err on the side of including slightly more text rather than cutting a policy mid-sentence.
- **When in doubt about the label**, ask: *"What student question does this text answer?"* Pick the label that matches.
- **Use the Notes field** in Label Studio for anything unusual — confusing structure, possible label disagreement, or uncertain edge cases. These notes help during annotation analysis.
- **Click Submit after every document**, even if you annotated nothing (e.g., the document was Invalid). Unsubmitted documents are not saved.

---

## 11. Quick Reference Card

| Question the text answers | Label |
|---|---|
| "What is this course about?" | DESCRIP |
| "How is my grade calculated?" | GRADE |
| "What do I need to do?" | ASSIGN |
| "When is it due / what if it's late?" | LATE |
| "Do I need to show up?" | ATTEND |
| "What do I need to buy?" | MATERIAL |
| "What is the schedule?" | SCHEDULE |
| "Can I cheat / use AI?" | INTEGRITY |
| "How do I contact the instructor?" | ADMIN |
| "How do I get accommodations?" | ACCOM |
| "How should I behave in class?" | CONDUCT |
| "Is there a hidden puzzle?" | CTF |
