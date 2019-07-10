import os, fnmatch
import argparse
from markdown import markdown
from bs4 import BeautifulSoup

def find_files(pattern, dir):
    result = []
    for root, dirs, files in os.walk(dir):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

def get_file_content(file_name):
    file = open(file_name, "r")
    content = file.read()
    file.close()

    return content

def write_obj_to_file(file_name, obj):
    file = open(file_name, "w")
    file.write(str(obj))
    file.close()

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

        self.md_html = BeautifulSoup(markdown(md_text), "html.parser")
        self.title = self.md_html.find_all()[0]

        html = BeautifulSoup("<!DOCTYPE html>\n<html></html>", "html.parser")
        html_root = html.find("html")

        html_root.append(self.create_html_head())
        self.container = self.define_md_container(html_root)

        self.conditional_processing()

        self.container.append(self.md_html)
        return html

    def conditional_processing(self):
        if self.args.r:
            self.title.extract()

        self.get_heading_numbering()

        if self.args.l:
            self.add_heading_links()

        if self.args.t != None:
            self.container.append(self.create_table_of_contents())

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
            header = self.soup.new_tag("div", id="header")
            title = self.soup.new_tag("span")
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
                res += " "
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

        contaier = self.soup.new_tag("div", id="toc")
        toc_title = self.soup.new_tag("h1")
        toc_title.string = self.args.toc_title

        contaier.append(toc_title)
        contaier.append(self.toc)

        return contaier

    def build_toc(self, level):
        self.toc = self.soup.new_tag("ol")

        self.hierarchy = [None, None, None, None, None]
        for element in self.md_html.find_all():
            elem_level = self.get_heading_level(element.name)
            elem_level = elem_level - self.min_level + 1

            if elem_level <= level:
                item = self.create_toc_item(element)
                parent, difference = self.get_parent_heading(elem_level)

                if level < 6:
                    self.hierarchy[elem_level - 1] = item

                contaier = self.create_item_container(item, parent, difference, elem_level)
                contaier.append(item)

    def create_toc_item(self, element):
        item = self.soup.new_tag("li")
        container = self.soup.new_tag("div")
        item.append(container)

        if self.args.l:
            index = next((i for i, t in enumerate(self.numbering) if t[0] == element), None)
            if index != None:
                elem_num = self.numbering[index]
                link = self.soup.new_tag("a", href="#" + self.generate_id(elem_num[1] + elem_num[0].string))
                container.append(link)
                container = link
            else:
                text =  self.soup.new_tag("p")
                container.append(text)
                container = text

        if element != None:
            container.string = element.string

        return item

    def get_parent_heading(self, elem_level):
        parent = None
        difference = 0

        if elem_level > 1:
            parent = self.hierarchy[elem_level - 2]

        if parent == None and elem_level > 1:
            parent, difference = self.get_nearest_parent(elem_level)

        if parent == None:
            parent = self.toc
        else:
            parent = parent.find("div")

        for i in range(elem_level, 4):
            self.hierarchy[i] = None

        return parent, difference

    def get_nearest_parent(self, elem_level):
        parent = None
        difference = 0

        for i in range(2, 6):
            if elem_level >= i:
                difference += 1
                if self.hierarchy[elem_level - i] != None:
                    parent = self.hierarchy[elem_level - i]
                    break

        return parent, difference

    def create_item_container(self, item, parent, difference, elem_level):
        if difference > 0:
            for i in range (0, difference):
                contaier = self.define_item_container(item, elem_level - difference + i)
                contaier['start'] = 0
                parent = self.create_toc_item(None)
                contaier.append(parent)
                self.hierarchy[elem_level - difference + i - 1] = parent
        else:
            contaier = self.define_item_container(parent, elem_level)

        return contaier

    def define_item_container(self, parent, level):
        contaier = parent.find("ol")

        if level == 1:
            contaier = self.toc
        elif contaier == None:
            contaier = self.soup.new_tag("ol")
            parent.append(contaier)

        return contaier

    def apply_numbering(self):
        for elem_num in self.numbering:
            elem_num[0].string = elem_num[1] + elem_num[0].string

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
    parser.add_argument('--header', action='store_true', help="add header to resulting html's body, header contains title")
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