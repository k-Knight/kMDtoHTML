# MdToHtml

Converter for **Markdown** into **HTML** (*+CSS &amp; JS*) written in Python

## Installation

The converter **requires** following Python libraries to fucntion:

- BeautifulSoup4
- Markdown

To install them you should run following commands
```
$ pip install beautifulsoup4
```
```
$ pip install Markdown
```

## Usage

The converter is designed to function from the command line. To see the list of possible arguments you can run the script with an ``-h`` or ``--help`` argument:

```
$ py MdToHtml.py -h
```

### Argument specification

|         Argument | Parameter type | Description                                                                                                                                |
| ---------------: | :------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
|       ``--file`` | String         | specify Markdown file to be converted to html                                                                                              |
|  ``--directory`` | String         | specify a directory that is searched recursively for Markdown (.md) files to be converted to html                                          |
|      ``--style`` | String         | specify a directory that is searched recursively for .css and .js files to be embeded in resulting html                                    |
|  ``--toc-title`` | String         | specify a title for table of contents, title is "Table of Contents" by default, takes effect only when ``-t`` parameter is specified       |
| ``--toc-number`` | None           | generate numbering for elements of table of contents                                                                                       |
|     ``--header`` | None           | add header to resulting html's body, header contains title                                                                                 |
|   ``--semantic`` | None           | use semantic html elements                                                                                                                 |
|           ``-r`` | None           | remove first element of the Markdown (always used as a title)                                                                              |
|           ``-n`` | None           | enumerate headings                                                                                                                         |
|           ``-l`` | None           | add an unique id to each heading to be referenceable                                                                                       |
|           ``-t`` | Integer        | add a table of contents to the begining of the html's body, provide an integer value for this parameter, specifying the depth of the table |