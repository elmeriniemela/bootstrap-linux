#! /bin/awk -f

function load_saved(   line, tabpos, key, value) {
    while ((getline line < saved) > 0) {
        tabpos = index(line, "\t")
        if (tabpos > 0) {
            key = substr(line, 1, tabpos - 1)
            value = substr(line, tabpos + 1)
            saved_map[key] = value
        }
    }
    close(saved)
}

function reset_entry() {
    entry_count = 0
    in_msgid = 0
    in_msgstr = 0
    msgid = ""
    msgstr = ""
}

function append_line(line) {
    entry_lines[++entry_count] = line
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

function po_unescape(str, s) {
    s = str
    gsub(/\\t/, "\t", s)
    gsub(/\\r/, "\r", s)
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
    gsub(/"/, "\\\"", s)
    gsub(/\n/, "\\n\"\n\"", s)
    return s
}

function flush_entry(   i, key, restored, replaced) {
    if (entry_count == 0) {
        return
    }

    key = msgid
    restored = 0

    if (key != "" && msgstr == "" && (key in saved_map)) {
        replaced = po_unescape(saved_map[key])

        for (i = 1; i <= entry_count; i++) {
            if (entry_lines[i] ~ /^msgstr[[:space:]]+"/) {
                print "msgstr \"" po_escape(replaced) "\""
                i++
                while (i <= entry_count && entry_lines[i] ~ /^[[:space:]]*"/) {
                    i++
                }
                for (; i <= entry_count; i++) {
                    print entry_lines[i]
                }
                restored = 1
                break
            } else {
                print entry_lines[i]
            }
        }
    }

    if (!restored) {
        for (i = 1; i <= entry_count; i++) {
            print entry_lines[i]
        }
    }

    print ""
    reset_entry()
}

BEGIN {
    if (ARGC != 3) {
        print "Usage: restore_i18n.awk <po_file> <saved_tsv>" > "/dev/stderr"
        exit 2
    }

    saved = ARGV[2]
    ARGV[2] = ""
    load_saved()
    reset_entry()
}

/^[[:space:]]*$/ {
    flush_entry()
    next
}

{
    append_line($0)
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
