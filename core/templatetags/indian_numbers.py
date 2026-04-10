from django import template
import decimal

register = template.Library()

@register.filter
def inr_format(value):
    """
    Formats a number in Indian style (Lakhs/Crores).
    1234567.89 -> 12,34,567.89
    """
    if value is None or value == "":
        return "0.00"
    
    try:
        # Convert to float and format to 2 decimal places
        val = float(value)
        is_negative = val < 0
        val = abs(val)
        
        s = "{:.2f}".format(val)
        parts = s.split('.')
        whole = parts[0]
        fraction = parts[1]
        
        if len(whole) <= 3:
            res = whole
        else:
            last_three = whole[-3:]
            remaining = whole[:-3]
            
            chunks = []
            while len(remaining) > 0:
                if len(remaining) >= 2:
                    chunks.insert(0, remaining[-2:])
                    remaining = remaining[:-2]
                else:
                    chunks.insert(0, remaining)
                    remaining = ""
            
            res = ",".join(chunks) + "," + last_three
            
        final_val = f"{res}.{fraction}"
        if is_negative:
            final_val = "-" + final_val
            
        return final_val
    except (ValueError, TypeError):
        return value
