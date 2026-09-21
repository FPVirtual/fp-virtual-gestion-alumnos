def creaEmailsDominio(nombre, pape, sape, documento):
    """
    Creamos un email para los estudiantes a partir de su nombre, apellidos y documento

    Marcos Ruiz García DNI 12345678T -> mruizg@fpvirtualaragon.es
    Juan Antonio Aragón de Lucía DNI 23456789G -> jaaragondlg@fpvirtualaragon.es
    Luis Miguel Saez de Burundanga DNI 56783456F -> lmsaezdbf@fpvirtualaragon.es
    """

    if sape is None:
        sape = ""

    if documento is None: #la función isAlumnoCreable no dejará crearlo luego
        documento = "-"

    print("creaEmailsDominio("+nombre+", "+pape+", "+sape+", "+documento+")")
    
    nombre = nombre.lower()
    nombre = eliminar_tildes_y_enes(nombre)

    pape = pape.lower()
    pape = pape.replace(' ', '')
    pape = eliminar_tildes_y_enes(pape)

    if sape is not None:
        sape = sape.lower()
        sape = eliminar_tildes_y_enes(sape)

    
    documento = documento.lower()
    documento = documento.replace(' ', '')

    palabras = nombre.split()
    inicialesNombre = ''.join([palabra[0] for palabra in palabras])

    inicialesSape = ""
    if sape is not None:
        palabras = sape.split()
        inicialesSape = ''.join([palabra[0] for palabra in palabras])

    generado = inicialesNombre + pape + inicialesSape + documento[-1] + "@fpvirtualaragon.es"

    #print(generado)

    return generado

def eliminar_tildes_y_enes(texto):
    
    texto = texto.replace("ñ", "n").replace("Ñ", "N")

    texto = texto.replace("á", "a").replace("Á", "A")
    texto = texto.replace("é", "e").replace("É", "E")
    texto = texto.replace("í", "i").replace("Í", "I")
    texto = texto.replace("ó", "o").replace("Ó", "O")
    texto = texto.replace("ú", "u").replace("Ú", "U")

    texto = texto.replace("à", "a").replace("À", "A")
    texto = texto.replace("é", "e").replace("È", "E")
    texto = texto.replace("ì", "i").replace("Ì", "I")
    texto = texto.replace("ò", "o").replace("Ò", "O")
    texto = texto.replace("ù", "u").replace("Ù", "U")
    
    texto = texto.replace("ä", "a").replace("Ä", "A")
    texto = texto.replace("ë", "e").replace("Ë", "E")
    texto = texto.replace("ï", "i").replace("Ï", "I")
    texto = texto.replace("ö", "o").replace("Ö", "O")
    texto = texto.replace("ü", "u").replace("Ü", "U")

    texto = texto.replace("â", "a").replace("Â", "A")
    texto = texto.replace("ê", "e").replace("Ê", "E")
    texto = texto.replace("î", "i").replace("Î", "I")
    texto = texto.replace("ô", "o").replace("Ô", "O")
    texto = texto.replace("û", "u").replace("Û", "U")

    texto = texto.replace("(", "").replace(")", "")

    texto = texto.replace("`", "").replace("'", "")

    
    return texto
