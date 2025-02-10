package AOB;

import java.util.Scanner;

public class Fibonacci {

	public static void main(String[] args) {
		Scanner sc = new Scanner(System.in);
        int numero;
        System.out.println("Numero:");
        numero = sc.nextInt();
        System.out.println("Fibonacci de " + numero + " es " + fibonacci(numero));
    }
	
    public static int fibonacci(int n) {
        if (n <= 1) {
            return n;
        } else {
            return fibonacci(n - 1) + fibonacci(n - 2);
        }
    }
}