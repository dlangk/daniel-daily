import os
import re
from pathlib import Path

from flask import Flask, render_template, jsonify, abort
import markdown
from markdown.extensions.toc import TocExtension

from src.storage import MarkdownStore


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    @app.template_filter('weekday')
    def weekday_filter(date_str):
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%A')
        except:
            return ''

    data_dir = Path(os.environ.get("DAILY_BRIEF_DATA", "./data"))
    store = MarkdownStore(
        content_dir=data_dir / "content",
        briefs_dir=data_dir / "briefs",
    )

    def render_brief_content(content: str, source_map: dict) -> str:
        source_pattern = r'\{sources?:\s*([^}]+)\}'

        def replace_sources(match):
            refs = [r.strip() for r in match.group(1).split(",")]
            superscripts = []
            for i, ref in enumerate(refs):
                ref = ref.strip()
                if ref in source_map:
                    path = source_map[ref]
                    superscripts.append(
                        f'<sup class="source-ref" data-path="{path}" data-ref="{ref}">{i + 1}</sup>'
                    )
            return '<span class="sources">' + "".join(superscripts) + '</span>'

        content = re.sub(source_pattern, replace_sources, content)

        md = markdown.Markdown(
            extensions=["tables", "fenced_code", TocExtension(permalink=False)]
        )
        html = md.convert(content)

        # Collect sources in order and remove their paragraphs
        sources_list = re.findall(r'<p>(<span class="sources">.*?</span>)</p>', html)
        html = re.sub(r'<p><span class="sources">.*?</span></p>', '', html)

        # Insert sources into h3 tags (they have id attributes)
        h3_pattern = r'(<h3[^>]*>)(.*?)(</h3>)'
        source_idx = [0]  # Use list to allow mutation in closure

        def insert_source(m):
            if source_idx[0] < len(sources_list):
                src = sources_list[source_idx[0]]
                source_idx[0] += 1
                return f'{m.group(1)}{m.group(2)} {src}{m.group(3)}'
            return m.group(0)

        html = re.sub(h3_pattern, insert_source, html)

        # Wrap each h3 + following content as an item for dividers
        h3_split = r'(<h3[^>]*>.*?</h3>)'
        parts = re.split(h3_split, html, flags=re.DOTALL)
        result = []
        in_item = False
        for part in parts:
            if re.match(r'<h3[^>]*>', part):
                if in_item:
                    result.append('</div>')
                result.append('<div class="brief-item">')
                result.append(part)
                in_item = True
            elif in_item and '<h2' in part:
                # Close item before h2
                idx = part.index('<h2')
                result.append(part[:idx])
                result.append('</div>')
                result.append(part[idx:])
                in_item = False
            else:
                result.append(part)
        if in_item:
            result.append('</div>')

        return ''.join(result)

    @app.route("/")
    def index():
        briefs_list = store.list_briefs()
        if not briefs_list:
            return render_template("brief.html", briefs=[])

        briefs = []
        for date_str, path in briefs_list:
            result = store.get_brief_by_date(date_str)
            if result:
                front_matter, content, _ = result
                source_map = front_matter.get("source_map", {})
                rendered = render_brief_content(content, source_map)
                briefs.append({
                    "date": date_str,
                    "front_matter": front_matter,
                    "content": rendered,
                })

        return render_template("brief.html", briefs=briefs)

    @app.route("/brief/<date>")
    def brief_by_date(date: str):
        result = store.get_brief_by_date(date)
        if not result:
            abort(404)

        front_matter, content, path = result
        source_map = front_matter.get("source_map", {})
        rendered = render_brief_content(content, source_map)

        return render_template(
            "brief.html",
            brief=front_matter,
            content=rendered,
            date=date,
        )

    @app.route("/archive")
    def archive():
        briefs = store.list_briefs()
        return render_template("archive.html", briefs=briefs)

    @app.route("/api/briefs")
    def api_briefs():
        briefs = store.list_briefs()
        return jsonify([{"date": date, "path": str(path)} for date, path in briefs])

    @app.route("/api/source/<path:source_path>")
    def api_source(source_path: str):
        content_file = store.get_content_by_path(source_path)
        if not content_file:
            abort(404)

        md = markdown.Markdown(extensions=["tables", "fenced_code"])
        rendered_content = md.convert(content_file.content)

        return jsonify({
            "title": content_file.title,
            "source_name": content_file.source_name,
            "url": content_file.url,
            "published_at": content_file.published_at.isoformat(),
            "author": content_file.author,
            "content": rendered_content,
        })

    return app
