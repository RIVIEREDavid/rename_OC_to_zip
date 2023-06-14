import re

var_str = "4523500156478942 is not a valid PO number. However, 5500000214 is a valid one, as well as 4500040484. ENQA5560 orENQA 556032are also both correct. I forgot to mention that 55023654862315456 and 450456464864862323 are also invalid PO"
regex = re.compile(r"(4|5)50\d{7}\s+|ENQA\s?\d{4,6}")
results = re.finditer(regex, var_str)
print(results)
po_list = [i.group() for i in re.finditer(regex, var_str)]
print(po_list)
for i in po_list:
    if len(i) > 10:
        po_list.remove(i)
print(po_list)



