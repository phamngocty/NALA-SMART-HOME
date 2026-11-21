import re
from html.parser import HTMLParser

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

class TagAuditor(HTMLParser):
    def __init__(self, target_id):
        super().__init__()
        self.target_id = target_id
        self.in_target = False
        self.stack = []
        self.errors = []
        self.current_id = None
        self.tag_count = 0

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        tag_id = attr_dict.get('id', '')
        if tag_id == self.target_id:
            self.in_target = True
            self.stack.append((tag, tag_id))
            return

        if self.in_target:
            # Self-closing void tags in HTML5
            if tag in ['img', 'input', 'br', 'hr', 'meta', 'link']:
                return
            self.stack.append((tag, tag_id))
            self.tag_count += 1

    def handle_endtag(self, tag):
        if not self.in_target:
            return
        if tag in ['img', 'input', 'br', 'hr', 'meta', 'link']:
            return
        if not self.stack:
            self.errors.append(f"Unexpected closing tag </{tag}> when stack is empty")
            return
        expected_tag, eid = self.stack.pop()
        if expected_tag != tag:
            self.errors.append(f"Mismatched tag: expected </{expected_tag}> (id={eid}), got </{tag}>")
        if not self.stack:
            self.in_target = False

modals = [
    'userProfileMemoryModal',
    'livingContextAutomationModal',
    'communicationModal',
    'systemSettingsModal'
]

print("=== CHECKING HTML TAG BALANCING FOR ALL 4 MODALS ===")
for m in modals:
    auditor = TagAuditor(m)
    auditor.feed(html)
    print(f"\nModal {m}:")
    print(f"  Processed tags: {auditor.tag_count}")
    print(f"  Unclosed tags remaining in stack: {len(auditor.stack)}")
    if auditor.stack:
        for s in auditor.stack[:5]:
            print(f"    Unclosed: <{s[0]} id='{s[1]}'>")
    if auditor.errors:
        print(f"  Tag errors: {len(auditor.errors)}")
        for e in auditor.errors[:5]:
            print(f"    {e}")
    else:
        print("  ✅ No tag nesting or unclosed tag errors!")
