# MOSH - Files to Delete (Cleanup Checklist)

## 🚨 CRITICAL - DELETE IMMEDIATELY
- [ ] `check_models.py` - **Contains exposed API key!** Delete immediately!

---

## Old PyInstaller Spec Files (Keep only `MOSH_ADA_Toolkit.spec`)
Delete all 30 old spec files:
- [ ] MOSH_ADA_Toolkit_v0.9.5.spec
- [ ] MOSH_ADA_Toolkit_v0.9.5_DEBUG.spec
- [ ] MOSH_ADA_Toolkit_v0.9.6_Test.spec
- [ ] MOSH_ADA_Toolkit_v0.9.6_Test2.spec
- [ ] MOSH_ADA_Toolkit_v0.9.6_Test3.spec
- [ ] MOSH_ADA_Toolkit_v0.9.6_Test4.spec
- [ ] MOSH_ADA_Toolkit_v0.9.6_Test5.spec
- [ ] MOSH_ADA_Toolkit_v0.9.6_Test6.spec
- [ ] MOSH_ADA_Toolkit_v0.9.6_Test7.spec
- [ ] MOSH_ADA_Toolkit_v0.9.6_Test8.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC1.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC2.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC3.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC4.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC5.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC6.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC7.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC8.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC9.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC10.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC16.spec
- [ ] MOSH_ADA_Toolkit_v1.0.0_RC17.spec
- [ ] MOSH_ADA_Toolkit_v2.spec
- [ ] MOSH_ADA_Toolkit_v3.spec
- [ ] MOSH_ADA_Toolkit_v4.spec
- [ ] MOSH_ADA_Toolkit_v5.spec
- [ ] MOSH_ADA_Toolkit_v6.spec

**Note:** Keep `MOSH_ADA_Toolkit.spec` (current version)

---

## Development & Testing Scripts (Functionality in GUI)
- [ ] `quick_test.py` - Single PDF test with hardcoded path
- [ ] `verify_conversion_temp.py` - QA verification with hardcoded paths
- [ ] `verify_math_crop.py` - Math detection verification script
- [ ] `verify_zip_fix.py` - ZIP creation test helper
- [ ] `reconvert.py` - Batch reprocessing (redundant with GUI)
- [ ] `compare_conversion.py` - Before/after comparison for testing
- [ ] `process_canvas_export.py` - Standalone IMSCC processor (functionality in toolkit_gui.py)
- [ ] `latex_converter.py` - Superseded by math_converter.py
- [ ] `fix_pptx_links.py` - Outdated, functionality in converter_utils.py
- [ ] `make_transparent.py` - Image transparency utility (not used in production)

---

## Test Data & Fixtures
- [ ] `test.html` - Generic test HTML
- [ ] `test.pdf` - Generic test PDF
- [ ] `test_img.txt` - Text fixture
- [ ] `test_source.png` - Test image
- [ ] `verification_test.html` - Test HTML file
- [ ] `Chapter 10 Note Packet (Key) (2).html` - Sample output, not test data

---

## Optional: Review & Consolidate Test Files
These test files should be consolidated into a proper pytest suite or deleted:
- [ ] `test_canvas_integration.py`
- [ ] `test_image_conversion.py`
- [ ] `test_manifest_sync.py`
- [ ] `test_marker_strip.py`
- [ ] `test_pattern.py`
- [ ] `test_pdf_conversion.py`
- [ ] `test_table_fix.py`

**Action:** Either consolidate into `tests/test_suite.py` or delete if not actively maintained

---

## Optional: Move to `/docs/planning/` (Not code, strategic docs)
Consider moving these to a separate planning folder to keep root clean:
- [ ] `USER_PERSONAS_EVALUATION.md`
- [ ] `GRANT_PROPOSAL_DRAFT.md`
- [ ] `VIRAL_MARKETING_STRATEGY.md`
- [ ] `VIDEO_TUTORIAL_SCRIPT.md`
- [ ] `competitive_analysis.md`

---

## Optional: Consolidate Build Documentation
These can be merged into a single `BUILD.md` file:
- [ ] `BUILD_GUIDE.md`
- [ ] `BUILD_MAC.md`
- [ ] Review `POPPLER_GUIDE.md` - might need consolidation

---

## Deletion Summary

**Total files to delete: 66**
- Critical: 1 (API key exposed)
- Old specs: 30
- Dev scripts: 10
- Test data: 6
- Test files: 7 (consolidate or delete)
- Strategic docs: 5 (optional, move to planning)
- Build docs: 3 (consolidate)

**Result:** Would reduce codebase to essential files only, improving clarity and maintainability.

---

## Additional Security Steps (After Deletion)

1. **Check git history** for exposed API keys:
   ```bash
   git log -p --all -- check_models.py | grep -i key
   ```

2. **Invalidate API key immediately** if it was actually used:
   - Go to Google Cloud Console
   - Regenerate the API key
   - Update `.env` or secure config

3. **Add to `.gitignore`:**
   ```
   # Secrets
   .env
   .env.local
   *.key
   *.secret
   config.local.json
   api_keys.py
   check_models.py
   ```

4. **Add pre-commit hook** to prevent future leaks:
   ```bash
   pip install detect-secrets
   detect-secrets scan --baseline .secrets.baseline
   ```

---

**Estimated time to clean up:** 30-45 minutes
**Impact:** Significantly cleaner, more maintainable codebase
