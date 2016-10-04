def sanitize(value):

    # convert to string and remove trailing spaces
    tvalue = str(value).strip()
    # only keep alpha numeric characters and replace the rest by "_"
    svalue = "".join(character if character.isalnum() else '.' for character in tvalue )
    return svalue