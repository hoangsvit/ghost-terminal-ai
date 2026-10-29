"""Offline checks for contribution pathways and first-boot GitHub references."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryHealthTests(unittest.TestCase):
    def test_expected_community_files(self):
        paths = [
            "LICENSE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
            "SECURITY.md", "SUPPORT.md", "CHANGELOG.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/dependabot.yml",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            ".github/ISSUE_TEMPLATE/documentation.yml",
            ".github/ISSUE_TEMPLATE/question.yml",
            "docs/REPOSITORY_MAINTENANCE.md",
        ]
        for path in paths:
            with self.subTest(path=path):
                p = ROOT / path
                self.assertTrue(p.is_file(), f"Missing {path}")
                self.assertTrue(p.read_text(encoding="utf-8").strip())

    def test_license_matches_declared_mit(self):
        license_text = (ROOT / "LICENSE").read_text()
        self.assertIn("MIT License", license_text)
        self.assertIn("Permission is hereby granted", license_text)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', license_text)
        self.assertIn("Copyright (c) 2026", license_text)

    def test_issue_forms_have_expected_schema_keys(self):
        template_dir = ROOT / ".github" / "ISSUE_TEMPLATE"
        for name in ("bug_report", "feature_request", "documentation", "question"):
            with self.subTest(form=name):
                text = (template_dir / (name + ".yml")).read_text()
                for key in ("name:", "description:", "body:", "  - type:", "      label:"):
                    self.assertIn(key, text)
                self.assertRegex(text, r"(?m)^\s+required: true\s*$")
        settings = (template_dir / "config.yml").read_text()
        self.assertIn("contact_links:", settings)
        self.assertIn("SECURITY.md", settings)

    def test_markdown_relative_links_resolve(self):
        paths = [
            "README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
            "SECURITY.md", "SUPPORT.md", "CHANGELOG.md",
            "docs/REPOSITORY_MAINTENANCE.md",
        ]
        pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
        for filename in paths:
            text = (ROOT / filename).read_text(encoding="utf-8")
            for raw in pattern.findall(text):
                target = raw.split("#", 1)[0].strip()
                if not target or target.startswith(("https://", "http://", "mailto:")):
                    continue
                with self.subTest(file=filename, link=raw):
                    self.assertTrue((ROOT / filename).parent.joinpath(target).exists())

    def test_docs_include_security_guidance(self):
        contributions = (ROOT / "CONTRIBUTING.md").read_text()
        self.assertIn("python3 -m unittest discover -s tests", contributions)
        self.assertIn("SECURITY.md", contributions)
        self.assertIn("private", (ROOT / "SECURITY.md").read_text().lower())
        self.assertIn("README", (ROOT / "SUPPORT.md").read_text())

    def test_first_boot_uses_default_branch(self):
        deploy = (ROOT / "vm" / "deploy.sh").read_text()
        startup = (ROOT / "vm" / "startup.sh").read_text()
        guide = (ROOT / "DEPLOY_COMPUTE_ENGINE.md").read_text()
        self.assertIn("/main/vm/startup.sh", deploy)
        self.assertIn("git clone --depth=1 --branch=main", startup)
        self.assertIn("vm/update.sh", guide)
        for source in (deploy, startup, guide):
            self.assertNotIn("feature/compute-engine-vm-gemma3", source)

    def test_ci_no_automatic_deployment_or_write_access(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("contents: read", ci)
        self.assertIn("python -m unittest discover -s tests -v", ci)
        self.assertIn("node --check public/scenarios.js", ci)
        self.assertNotIn("pull_request_target:", ci)
        self.assertNotIn("vm/update.sh --ref main", ci)
        dependabot = (ROOT / ".github/dependabot.yml").read_text()
        self.assertIn('package-ecosystem: "github-actions"', dependabot)
        self.assertNotIn("auto-merge", dependabot)


if __name__ == "__main__":
    unittest.main()
