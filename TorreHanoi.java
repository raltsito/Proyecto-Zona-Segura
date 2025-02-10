package AOB;

import java.util.Scanner;

public class TorreHanoi {
	
	public static void main(String[] args) {
		Scanner sc = new Scanner(System.in);
        int discos;
        System.out.println("Numero de discos de la torre:");
        discos = sc.nextInt();
        hanoi(discos,"A","C","B");
    }
	
	public static void hanoi(int n,String origen,String destino,String auxiliar) {
        if (n==1) {
            System.out.println("Mover disco 1 de "+origen+" a "+destino);
        } else {
            hanoi(n-1, origen, auxiliar, destino);
            System.out.println("Mover disco "+n+" de "+origen+" a "+destino);
            hanoi(n-1,auxiliar,destino,origen);
        }
    }
}
