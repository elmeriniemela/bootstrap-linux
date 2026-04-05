#! /bin/awk -f

function reset_entry() {
    in_msgid = 0
    in_msgstr = 0
    msgid = ""
    msgstr = ""
}

function po_unquote(line, s) {
    s = line
    sub(/^[[:space:]]*"/, "", s)
    sub(/"[[:space:]]*$/, "", s)
    gsub(/\\n/, "\n", s)
    gsub(/\\"/, "\"", s)
    gsub(/\\\\/, "\\", s)
    return s
}

function po_escape(str, s) {
    s = str
    gsub(/\\/, "\\\\", s)
    gsub(/\t/, "\\t", s)
    gsub(/\r/, "\\r", s)
    gsub(/\n/, "\\n", s)
    gsub(/"/, "\\\"", s)
    return s
}

function flush_entry() {
    if (msgid != "" && msgstr != "") {
        print po_escape(msgid) "\t" po_escape(msgstr) >> out
    }
    reset_entry()
}

BEGIN {
    if (ARGC != 3) {
        print "Usage: extract_i18n.awk <po_file> <out_tsv>" > "/dev/stderr"
        exit 2
    }

    out = ARGV[2]
    ARGV[2] = ""
    reset_entry()
}

/^[[:space:]]*$/ {
    flush_entry()
    next
}

/^msgid[[:space:]]+"/ {
    in_msgid = 1
    in_msgstr = 0
    msgid = po_unquote(substr($0, index($0, "\"")))
    next
}

/^msgstr[[:space:]]+"/ {
    in_msgid = 0
    in_msgstr = 1
    msgstr = po_unquote(substr($0, index($0, "\"")))
    next
}

/^[[:space:]]*"/ {
    if (in_msgid) {
        msgid = msgid po_unquote($0)
    } else if (in_msgstr) {
        msgstr = msgstr po_unquote($0)
    }
    next
}

END {
    flush_entry()
}
