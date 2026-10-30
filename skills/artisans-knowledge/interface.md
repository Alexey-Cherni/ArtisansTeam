# Interface card

Adapted from the example team's interface card. `/artisans-knowledge` applies it only when the project has a user interface (pages, screens, components). It names no framework; `PROJECT-OVERVIEW.md → User interface` says what each term is in this project.

## Heuristics

Each one is a check. A review finding cites the heuristic's number.

- **H1 Status is visible.** Every action that takes time or changes data shows feedback in place: what happened, and how many. Show a loading state while it takes time.
- **H2 The user's words.** Labels, headings and error text use the domain's words, not identifiers, codes or column names.
- **H3 A way back.** Destructive and bulk actions confirm with the count and the consequence, or show a preview before applying.
- **H4 One way to do one thing.** The same action uses the same word, place and control on every page.
- **H5 Errors prevented.** Don't offer invalid choices. Mark required fields, and show the expected format beside the field.
- **H6 Recognise, do not recall.** Where a person picks a reference to something, show its name, not a code they must remember.
- **H7 The frequent task is short.** Daily tasks need no repeated confirmations and no re-entered filters.
- **H8 The eye lands where the task is.** Each view has one visible primary action. The key column comes first, and figures that are compared line up.
- **H9 An error says what to do.** Say what happened, what the person can do, and where. Never just "something went wrong".
- **H10 Help where the hand is.** Show the format, unit or example beside the field that needs it.
- **H11 Reachable without a pointer.** Keyboard order follows the task, focus returns to the control that opened a dialog, and every icon-only control has an accessible name.
- **H12 Readable.** Contrast and target sizes match the project's own styles, and meaning is never carried by colour alone.

## States

Describe every new view and action in six states:

| State | What must be shown |
|-------|--------------------|
| empty | that there is nothing yet, and the one action that changes that |
| loading | that data is on its way, in place of where it will appear |
| error | H9: what happened, what to do |
| partial | which part succeeded, which did not, and why (bulk actions, uploads) |
| success | H1: what happened and how many |
| no permission | that the action exists, that this person cannot do it, and who can |

## Review checks

Copy these into `REVIEW-CHECKLIST.md`, each rewritten with the project's own element and path.

1. Every new list or detail view has an empty state with text (never a blank area), and a loading state where its data arrives after the page.
2. Every new action that changes data gives feedback through the project's feedback element, naming what changed and how many.
3. Every new destructive or bulk action confirms with the count and the consequence, or shows a preview before applying.
4. Every new error path shows text that says what happened and what to do. Never a code or an identifier alone.
5. Every new control has a visible label, or, when it is icon-only, an accessible name and a title. Every new field that needs a format shows it beside the field.
6. A new page puts its primary action where the project's other pages put theirs, and uses the project's word for it.
7. New interface copy is in the project's interface language, exact, with no placeholder text.

## Sources

- Nielsen, "10 Usability Heuristics for User Interface Design" (H1–H10, reworded as checks).
- WCAG 2.2 level AA (H11, H12).
