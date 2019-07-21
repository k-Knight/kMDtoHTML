import os, fnmatch
import argparse
import bs4
import codecs
from markdown import markdown
from bs4 import BeautifulSoup
from types import SimpleNamespace

def find_files(pattern, dir):
    result = []
    for root, dirs, files in os.walk(dir):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

def get_file_content(file_name):
    file = codecs.open(file_name, "r", "utf-8")
    content = file.read()
    file.close()

    return content

def write_obj_to_file(file_name, obj):
    file = codecs.open(file_name, "w", "utf-8")
    file.write(str(obj))
    file.close()

def elem_to_str(element, before = ""):
    res = before + str(element)
    res = res.replace("\n", "")
    if len(res) > 153:
        res = res[:150] + "..."

    return res

class Section:
    def __init__(self, element, content, level = 7):
        self.element = element
        self.content = content
        self.level = level

    def __str__(self, before = ""):
        result = elem_to_str(self.element, before) + "\n"

        for child in self.content:
            result += child.__str__(before + "| ")

        return result


class MDHtml:
    def __init__(self, file_name, args):
        self.args = args
        self.soup = BeautifulSoup("", 'html.parser')
        self.file_name = file_name

    def convert_to_html(self):
        try:
            md_text = get_file_content(self.file_name)
        except:
            print("WARNING: Failed to load file: " + self.file_name)
            return

        if self.args.verbose:
            print("INFO: Convertion started for  " + self.file_name)

        md_extensions = ['extra', 'admonition', 'codehilite']
        self.md_html = BeautifulSoup(markdown(md_text, extensions=md_extensions), "html.parser")
        self.preprocess_symbols()
        self.title = self.md_html.find_all()[0]

        html = BeautifulSoup("<!DOCTYPE html>\n<html></html>", "html.parser")
        html_root = html.find("html")

        html_root.append(self.create_html_head())
        self.container = self.define_md_container(html_root)

        self.conditional_processing()

        if self.args.semantic:
            article = self.soup.new_tag("article")
            self.container.append(article)
            self.container = article

        self.container.append(self.md_html)
        return html

    def preprocess_symbols(self):
        strings = self.find_strings_to_preprocess()

        for string in strings:
            processed_string = str(string)

            processed_string = self.replace_dashes(processed_string)

            string.replace_with(BeautifulSoup(processed_string, "html.parser"))

    def find_strings_to_preprocess(self):
        strings = []
        elem_stack = []
        for element in self.md_html.find_all(True, recursive=False):
            elem_stack.append(SimpleNamespace(tag = element, inside_text = False))

        while len(elem_stack) > 0:
            element = elem_stack.pop()
            self.set_element_flags(element)

            for child in element.tag.contents:
                if element.string_extraction_allowed and type(child) == bs4.element.NavigableString:
                    strings.append(child)

                if element.children_extraction_allowed and type(child) == bs4.element.Tag:
                    elem_stack.append(SimpleNamespace(tag = child, inside_text = element.is_text))

        return strings

    def set_element_flags(self, element):
        element.is_text = element.tag.name in [
            "p", "figcaption", "blockquote",
            "caption", "cite", "dt", "dd", "del",
            "ins", "details", "dfn", "summary",
            "h1", "h2", "h3", "h4", "h5", "h6",
            "li", "mark", "q", "s", "sub", "sup",
            "td", "th", "var"
            ]

        element.children_extraction_allowed = not element.tag.name in ["code", "pre", "kbd", "samp"]

        element.string_extraction_allowed = element.is_text or (
                element.inside_text and
                element.tag.name in ["strong", "em", "span", "b", "i", "span", "u"] and
                element.children_extraction_allowed
            )

    def replace_dashes(self, string):
        string = string.replace("---", "&mdash;")
        string = string.replace("--", "&ndash;")

        return string

    def conditional_processing(self):
        if self.args.r:
            self.title.extract()

        self.get_heading_numbering()

        if self.args.l:
            self.add_heading_links()

        if self.args.t != None or self.args.semantic:
            self.define_md_structure()

            if self.args.verbose:
                print("\n" + 153 * "=" + "\n" + 71 * "=" + " HIERARCHY " + 71 * "=" + "\n" + 153 * "=" + "\n")
                for section in self.hierarchy: print(section)

            if self.args.t != None:
                self.container.append(self.create_table_of_contents())

            if self.args.semantic:
                self.semantic_restructure()

        if self.args.n:
            self.apply_numbering()

    def create_html_head(self):
        head = self.soup.new_tag("head")
        head.append(self.soup.new_tag("meta", charset="UTF-8"))

        head_title = self.soup.new_tag("title")
        head_title.string = self.title.string
        head.append(head_title)

        if self.args.style != None:
            self.append_styles(head)

        return head

    def append_styles(self, container):
        css_files = find_files("*.css", self.args.style)
        js_files =  find_files("*.js",  self.args.style)

        if len(css_files) + len(js_files) < 1:
            print("WARNING: No styles were found")
            return

        for file_name in css_files:
            css = self.create_tag_from_file("style", file_name)
            if css != None:
                container.append(css)

        for file_name in js_files:
            js = self.create_tag_from_file("script", file_name)
            if js != None:
                container.append(js)

    def create_tag_from_file(self, tag_name, file_name):
        try:
            text = get_file_content(file_name)
        except:
            print("WARNING: Failed to load file: " + file_name)
            return None

        tag = self.soup.new_tag(tag_name)
        tag.string = text

        return tag

    def define_md_container(self, container):
        md_container = self.soup.new_tag("body")
        container.append(md_container)

        if self.args.header:
            header = self.soup.new_tag("div" if not self.args.semantic else "header", id="header")
            title = self.soup.new_tag("span" if not self.args.semantic else "h1")
            title.string = self.title.string
            header.append(title)
            md_container.append(header)

            content = self.soup.new_tag("div", id="content")
            md_container.append(content)
            return content
        else:
            return md_container

    def get_heading_numbering(self):
        self.min_level = 7

        for element in self.md_html.find_all():
            level = self.get_heading_level(element.name)
            if self.min_level > level:
                self.min_level = level

        self.numbering = []
        number = [0, 0, 0, 0, 0, 0]

        for element in self.md_html.find_all():
            level = self.get_heading_level(element.name)

            if level < 7:
                level = level - self.min_level + 1
                self.update_numbering(number, level)
                self.numbering.append((element, self.get_numbering_str(number, level)))

    def get_numbering_str(self, numbering, level):
        res = ""
        for i in range(0, 5):
            if i < level:
                res += str(numbering[i]) + "."
            else:
                res = res[:-1]
                return res

    def update_numbering(self, numbering, level):
        numbering[level - 1] += 1
        for i in range(level, 5):
            numbering[i] = 0

    def get_heading_level(self, heading):
        if   heading == "h1": return 1
        elif heading == "h2": return 2
        elif heading == "h3": return 3
        elif heading == "h4": return 4
        elif heading == "h5": return 5
        elif heading == "h6": return 6
        else:
            return 7

    def add_heading_links(self):
        for elem_num in self.numbering:
            elem_num[0]['id'] = self.generate_id(elem_num[1] + elem_num[0].string)

    def generate_id(self, content):
        res = ""
        space_added = False

        for char in content:
            if char.isalnum():
                res += char
                space_added = False
            else:
                if not space_added:
                    res += "-"
                    space_added = True

        return res

    def define_md_structure(self):
        self.hierarchy = []
        section_stack = [None, None, None, None, None, None]

        for element in self.md_html.find_all(True, recursive=False):
            elem_level = self.get_heading_level(element.name)
            elem_level = elem_level - self.min_level + 1

            if elem_level < 7:
                section = Section(element, [], elem_level)
                self.append_section_to_hierarchy(section, section_stack)

                for i in range(elem_level, 6):
                    section_stack[i] = None
            else:
                for i in range(len(section_stack) -1, -1, -1):
                    if section_stack[i] != None:
                        section_stack[i].content.append(Section(element, []))
                        break
                    elif i == 0:
                        self.hierarchy.append(Section(element, []))

    def append_section_to_hierarchy(self, section, section_stack):
        if section.level == 1:
            self.hierarchy.append(section)
            section_stack[0] = section
        else:
            append_stack = [section]
            for i in range(section.level - 2, -1 , -1):
                if section_stack[i] == None:
                    append_stack.append(Section(None, [], i + 1))
                else:
                    break

            while len(append_stack) > 0:
                append_section = append_stack.pop()
                section_stack[append_section.level - 1] = append_section

                if append_section.level == 1:
                    self.hierarchy.append(append_section)
                else:
                    section_stack[append_section.level - 2].content.append(append_section)

    def create_table_of_contents(self):
        try:
            level = int(self.args.t)
            if level < 1: level = 1
            elif level > 6: level = 6
        except:
            level = 4

        if self.args.toc_title == None:
            self.args.toc_title = "Table of Contents"

        self.build_toc(level)

        contaier = self.soup.new_tag("div" if not self.args.semantic else "section", id="toc")
        toc_title = self.soup.new_tag("h1")
        toc_title.string = self.args.toc_title

        contaier.append(toc_title)
        contaier.append(self.toc)

        return contaier

    def build_toc(self, level):
        self.toc = self.soup.new_tag("ol")
        section_stack = [SimpleNamespace(
            element  = self.toc,
            children = self.hierarchy,
            level    = 0,
            parent   = None
        )]

        while len(section_stack) > 0:
            element = section_stack.pop()

            if element.level <= level:
                if element.level > 0:
                    item = self.create_toc_item(element)
                    parent = SimpleNamespace(element = item.find("div"), level = element.level)
                    self.define_item_container(element.parent.element, element.level).append(item)
                else:
                    parent = SimpleNamespace(element = element.element, level = element.level)

                for i in range(len(element.children) - 1, -1, -1):
                    section_stack.append(SimpleNamespace(
                        element  = element.children[i].element,
                        children = element.children[i].content,
                        level    = element.children[i].level,
                        parent   = parent
                    ))

    def create_toc_item(self, section):
        item = self.soup.new_tag("li")
        index = next((i for i, t in enumerate(self.numbering) if t[0] == section.element), None)

        if index != None:
            if self.args.toc_number:
                num = self.soup.new_tag("span", attrs={"class": "toc-number"})
                num.string = self.numbering[index][1]
                item.append(num)

            if self.args.l:
                elem_num = self.numbering[index]
                element = self.soup.new_tag("a", href="#" + self.generate_id(elem_num[1] + elem_num[0].string))
        else:
            element =  self.soup.new_tag("span")

        container = self.soup.new_tag("div")
        item.append(container)
        container.append(element)
        container = element
        container.string = section.element.string if section.element != None else ""

        return item

    def define_item_container(self, parent, level):
        contaier = parent.find("ol")

        if level == 1:
            contaier = self.toc
        elif contaier == None:
            contaier = self.soup.new_tag("ol")
            parent.append(contaier)

        return contaier

    def semantic_restructure(self):
        semantic_html = BeautifulSoup("", "html.parser")
        section_stack = []

        for section_l1 in self.hierarchy:
            section_stack.append([section_l1, 0, semantic_html, None])
            while len(section_stack) > 0:
                section_element = section_stack[-1]

                if section_element[3] == None:
                    if section_element[0].level < 7:
                        section = self.soup.new_tag("section")
                        if section_element[0].element != None:
                            section.append(section_element[0].element)
                        section_element[3] = section
                        section_element[2].append(section)
                    else:
                        section_element[2].append(section_element[0].element)

                while True:
                    if section_element[1] >= len(section_element[0].content):
                        section_stack.pop()
                        break

                    content_element = section_element[0].content[section_element[1]]
                    section_element[1] += 1

                    if content_element.level < 7:
                        section_stack.append([content_element, 0, section_element[3], None])
                        break
                    else:
                        section_element[3].append(content_element.element)

        self.md_html = semantic_html

    def apply_numbering(self):
        for elem_num in self.numbering:
            elem_string = elem_num[0].string
            elem_num[0].string = ""

            num = self.soup.new_tag("span", attrs={"class": "heading-number"})
            num.string = elem_num[1]
            elem_num[0].append(num)
            elem_num[0].append(elem_string)

class Converter:
    def __init__(self, args):
        self.args = args

    def run_conversions(self):
        if self.args.directory != None:
            self.convert_all_to_html(self.args.directory)
        if self.args.file != None:
            self.convert_file(self.args.file)

    def convert_all_to_html(self, dir):
        files = find_files("*.md", dir)

        if len(files) < 1:
            print("WARNING: No markdown files found")
            return

        for file_name in files:
            self.convert_file(file_name)

    def convert_file(self, file_name):
        md_html = MDHtml(file_name, self.args)
        html = md_html.convert_to_html()
        write_obj_to_file(os.path.splitext(file_name)[0] + ".html", html)

def main():
    parser = argparse.ArgumentParser(description="Markdown to HTML coverter")
    parser.add_argument('--file', type=str, help="specify Markdown file to be converted to html")
    parser.add_argument('--directory', type=str, help="specify a directory that is searched recursively for Markdown (.md) files to be converted to html")
    parser.add_argument('--style', type=str, help="specify a directory that is searched recursively for .css and .js files to be embeded in resulting html")
    parser.add_argument('--toc-title', type=str, help="specify a title for table of contents, title is \"Table of Contents\" by default, takes effect only when -t parameter is specified")
    parser.add_argument('--toc-number', action='store_true', help="generate numbering for elements of table of contents")
    parser.add_argument('--header', action='store_true', help="add header to resulting html's body, header contains title")
    parser.add_argument('--semantic', action='store_true', help="use semantic html elements")
    parser.add_argument('--verbose', action='store_true', help="print debug infromation")
    parser.add_argument('-r', action='store_true', help="remove first element of the Markdown (always used as a title)")
    parser.add_argument('-n', action='store_true', help="enumerate headings")
    parser.add_argument('-l', action='store_true', help="add an unique id to each heading to be referenceable")
    parser.add_argument('-t', type=int, help="add a table of contents to the begining of the html's body, provide an integer value for this parameter, specifying the depth of the table")

    args = parser.parse_args()
    if args.directory == None and args.file == None:
            print("ERROR: no action specified\n")
            parser.print_help()

    converter = Converter(args)
    converter.run_conversions()

if __name__== "__main__":
    main()