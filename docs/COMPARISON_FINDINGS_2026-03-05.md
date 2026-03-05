# Comparison Findings (2026-03-05)

## Scope compared
- Original export: test_temp_be95c3c0/meri-quick-test-165-module-1-export_extracted
- Converted export: test_temp_be95c3c0/math-ada-test-export_extracted

## High-impact errors found

1) Module items still point to Attachment resources (not Wiki Pages)
- In converted module metadata, the converted items are still `content_type=Attachment` and reference `web_resources/*.html` resources, not `wiki_content/*.html` resources.
- Evidence: [course_settings/module_meta.xml](../test_temp_be95c3c0/math-ada-test-export_extracted/course_settings/module_meta.xml#L12-L63), [course_settings/module_meta.xml](../test_temp_be95c3c0/math-ada-test-export_extracted/course_settings/module_meta.xml#L95-L159)
- Impact: Canvas treats these as file/attachment-type items (HTML file behavior), not true Wiki Page items.

2) New Wiki resources exist but are orphaned (unused by modules)
- `imsmanifest.xml` contains 8 `wiki_content/*.html` resources, but none are referenced by module `identifierref`.
- Evidence: [imsmanifest.xml](../test_temp_be95c3c0/math-ada-test-export_extracted/imsmanifest.xml#L142-L164) and module references in [course_settings/module_meta.xml](../test_temp_be95c3c0/math-ada-test-export_extracted/course_settings/module_meta.xml)
- Impact: The correct converted pages exist but learners/instructors are routed to attachment HTML targets instead.

3) Missing images in the pages users actually open (web_resources HTML)
- Original package had 8 `*_graphs` folders under `web_resources`; converted package has none.
- But converted `web_resources/*.html` still references `*_graphs/...png` paths.
- Missing image refs in converted `web_resources` pages: 48 total.
- Affected pages and missing ref count:
  - Chapter 2 Note Packet (3).html: 21
  - Chapter 2 Note Packet (Key) (4).html: 14
  - Chapter 3 Note Packet (3).html: 3
  - Chapter 3 Note Packet (Key) (4).html: 1
  - Mat 165 Blank Graphs for practice (2).html: 6
  - Mat 165 Classwork Sections 2.html: 1
  - trig_cheat_sheet (4).html: 1
  - Unit Circle Trig (1).html: 1
- Evidence sample: [web_resources/Unit Circle Trig (1).html](../test_temp_be95c3c0/math-ada-test-export_extracted/web_resources/Unit%20Circle%20Trig%20(1).html#L64)
- Impact: “Some images do not appear” on imported content when users land on these attachment pages.

4) Residual GRAPH_BBOX token leaked into image `src`
- Found unresolved token in converted output:
- Evidence: [web_resources/Mat 165 Classwork Sections 2.html](../test_temp_be95c3c0/math-ada-test-export_extracted/web_resources/Mat%20165%20Classwork%20Sections%202.html#L11)
- Impact: invalid `img src`, guaranteed broken image.

5) Formula rendering risk in attachment HTML targets
- Because modules route to `web_resources/*.html` attachment targets, formulas are not consistently rendered as Canvas page math in that flow.
- Additional signal: unbalanced inline math delimiters detected in some converted files:
  - web_resources/Chapter 2 Note Packet (Key) (4).html
  - web_resources/Chapter 3 Note Packet (Key) (4).html
  - wiki_content/chapter-3-note-packet-key-4.html
- Impact: visible raw LaTeX in some contexts and inconsistent rendering.

## What is actually correct right now
- `wiki_content/*.html` pages point image `src` to `$IMS-CC-FILEBASE$/remediated_images/...` and those assets exist.
- This path set appears internally consistent; issue is that module routing does not use these resources.

## Root-cause summary
- Conversion added new wiki resources but did not complete the module reference migration from old attachment/web_resources identifiers to new wiki_content identifiers.
- Legacy `web_resources` HTML still references removed `*_graphs` directories after asset relocation to `remediated_images`.
- One token-cleanup miss (`[GRAPH_BBOX: ...]`) remained in `web_resources` output.
