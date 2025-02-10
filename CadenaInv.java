package AOB;

public class CadenaInv {

	public static String CadenaInve(String cadena) {
	   if (cadena.isEmpty()) {
	       return cadena;
	   } else {
	       return CadenaInve(cadena.substring(1)) + cadena.charAt(0);
	   }
	}

	public static void main(String[] args) {
	    String cadena = "Abecedario";
	    System.out.println("Cadena invertida: " + CadenaInve(cadena));
	    }
	}
	