"""Verify caption-to-panel correspondence and generated grouped HTML."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import report_lint
import md_to_html
from bs4 import BeautifulSoup
from PIL import Image


class FigurePanelTests(unittest.TestCase):
    def test_image_alt_text_is_not_a_bibliography_key(self):
        self.assertEqual(report_lint._citation_keys('![THEM6](a.png)\n![KEGG](b.png)\n[Wolf2018Scanpy]'),
                         {'Wolf2018Scanpy'})

    def test_gallery_paths_and_repeated_sample_names_are_not_a_sample_list(self):
        markdown = '\n'.join(f'![指标](GSM9086919/GSM9086919_metric{i}.png)' for i in range(4))
        markdown += '\n\n**图1.** ' + '；'.join(f'{letter}：GSM9086919 指标' for letter in 'ABCD')
        report = report_lint.LintReport()
        report_lint.check_sample_information_tables(markdown, report)
        self.assertFalse(report.errors)

    def test_real_sample_identifier_list_still_requires_a_table(self):
        report = report_lint.LintReport()
        report_lint.check_sample_information_tables('样本为 GSM9086919、GSM9086920、GSM9086921、GSM9086922。', report)
        self.assertTrue(report.errors)

    def gallery_dom(self):
        soup = BeautifulSoup('''
        <figure class="figure"><div class="figure-scroll">
        <a class="img-link" data-panel-label="A"><img src="one.png"></a>
        <a class="img-link" data-panel-label="B"><img src="two.png"></a>
        </div><figcaption>图1. A：一；B：二。</figcaption></figure>
        <figure class="figure"><div class="figure-scroll">
        <a class="img-link" data-panel-label="A"><img src="three.png"></a>
        <a class="img-link" data-panel-label="B"><img src="four.png"></a>
        </div><figcaption>图2. A：三；B：四。</figcaption></figure>
        ''', 'html.parser')
        return soup

    def test_each_gallery_has_one_number_and_restarts_at_a(self):
        self.assertEqual(md_to_html.validate_figure_galleries(self.gallery_dom()),
                         {"figures": 2, "galleries": 2, "panels": 4})

    def test_legacy_wrapper_of_separately_numbered_figures_is_rejected(self):
        soup = self.gallery_dom()
        wrapper = soup.new_tag('section', attrs={'class': 'content-gallery'})
        for figure in list(soup.select('figure')):
            wrapper.append(figure.extract())
        soup.append(wrapper)
        with self.assertRaisesRegex(ValueError, 'separately numbered'):
            md_to_html.validate_figure_galleries(soup)

    def test_panel_numbers_cannot_continue_into_next_gallery(self):
        soup = self.gallery_dom()
        soup.select('[data-panel-label]')[2]['data-panel-label'] = 'C'
        with self.assertRaisesRegex(ValueError, 'panel labels'):
            md_to_html.validate_figure_galleries(soup)

    def test_multiple_caption_numbers_in_one_gallery_are_rejected(self):
        soup = self.gallery_dom()
        soup.select_one('figcaption').string = '图1. A：一；图2. B：二。'
        with self.assertRaisesRegex(ValueError, 'one sequential figure number'):
            md_to_html.validate_figure_galleries(soup)

    def check_caption(self, caption, count=4):
        markdown = "\n".join(f"![](panel{i}.png)" for i in range(count))
        report = report_lint.LintReport()
        report_lint.check_figure_numbering_and_captions(markdown + "\n\n**图1.** " + caption, report)
        return report.errors

    def test_each_panel_is_explained(self):
        self.assertFalse(self.check_caption("结果。A：第一张；B：第二张；C：第三张；D：第四张。"))

    def test_caption_can_start_directly_with_panel_a(self):
        self.assertFalse(self.check_caption("A：一；B：二；C：三；D：四。"))

    def test_multiline_caption(self):
        self.assertFalse(self.check_caption("结果。\nA：一；B：二；\nC：三；D：四。"))

    def test_ranges_cover_consecutive_panels(self):
        self.assertFalse(self.check_caption("结果。A：第一张；B–D：其余三张。"))

    def test_missing_panel_explanation_fails(self):
        self.assertTrue(self.check_caption("结果。A：第一张；B：第二张；C：第三张。"))

    def test_misordered_panel_explanations_fail(self):
        self.assertTrue(self.check_caption("结果。B：第二张；A：第一张；C：第三张；D：第四张。"))

    def test_single_image_needs_no_panel_letter(self):
        self.assertFalse(self.check_caption("单图说明。", count=1))

    def test_letters_continue_after_z(self):
        self.assertFalse(self.check_caption("结果。A–Z：前26张；AA：第27张。", count=27))

    def test_generated_html_keeps_shared_caption_and_original_pdf_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(5):
                Image.new("RGB", (20, 20), "white").save(root / f"panel{index}.png")
                (root / f"panel{index}.pdf").write_bytes(b"%PDF-1.4\n")
            grouped = "\n".join(f"![](panel{i}.png)" for i in range(4))
            markdown = grouped + "\n\n**图1.** 结果。A：一；B：二；C：三；D：四。\n\n![](panel4.png)\n\n**图2.** 单图。"
            html, broken = md_to_html.convert(markdown, title="Panels", asset_base=root, allow_raw_html=False, output_path=root / "Report.html")
            self.assertFalse(broken)
            soup = BeautifulSoup(html, "html.parser")
            figures = soup.select("figure.figure")
            self.assertEqual(len(figures), 2)
            self.assertEqual([node["data-panel-label"] for node in figures[0].select("[data-panel-label]")], list("ABCD"))
            self.assertEqual(len(figures[0].select("figcaption")), 1)
            self.assertEqual([node["href"] for node in figures[0].select("a.img-link")], [f"panel{i}.pdf" for i in range(4)])
            self.assertFalse(figures[1].select("[data-panel-label]"))
            self.assertEqual(md_to_html.validate_figure_galleries(soup),
                             {"figures": 2, "galleries": 1, "panels": 5})
            styles = "\n".join(node.get_text() for node in soup.select("style"))
            rule = styles.split(".figure-scroll .img-link::before {", 1)[1].split("}", 1)[0]
            self.assertIn("opacity: 1", rule)


if __name__ == "__main__":
    unittest.main()
