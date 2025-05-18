# CRT
## Introducción
Este repositorio describe el proyecto realizado para la asignatura "Control mediante Real-Time Linux", en este proyecto se utilia una Raspberry Pi 4B de 8GB de RAM para implementar una aplicacion en tiempo real. La aplicacion a implementar se trata de un programa que incrementa y decrementa en tiempo real un contador en funcion de los pulsos detectados en dos pares de fototransistores, el valor del contador se muestra en una pantalla OLED de 0,96" controlada mediante i2c. Adicionalmente hay un boton que simula una parada de emergencia, su unica funcion es encender un LED rojo.


## Kernel
Para poder realzar aplicaciones en tiempo real se instala un Kernel en tiempo real que nos permitira utilizar un scheduler diferente, a continuacion se explica el procedimiento llevado a cabo para descargar el codigo fuente del Kernel, configurarlo y compilarlo,  

## Descarga del Kernel y el parche
Accedemos a la documentacion oficial de Raspberry Pi mediante el siguiente link
https://www.raspberrypi.com/documentation/computers/linux_kernel.html

Descarga del codigo fuente desde el repositorio oficial
>git clone --depth=1 https://github.com/raspberrypi/linux

Descargamos y aplicammos el parche de tiempo real obtenido mediante
>wget https://www.kernel.org/pub/linux/kernel/projects/rt/6.6/patch-6.6.77-rt50.patch.gz

Descomprimimos el fichero usando
>gunzip patch-6.6.77-rt50.patch

Lo movemos al interior de la carpeta linux y parcheamos mediante el siguiente comando

### Aplicamos el parche
>patch -p1 < patch-6.6.77-rt50.patch

## Configuración y compilación del Kernel
Configuramos el Kernel para nuestra Raspberry Pi 4B de 64 bits
>cd linux  
>KERNEL=kernel8  
>make bcm2711_defconfig

Configuramos las opciones del Kernel utilizando 
>make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- menuconfig

Dentro de la ventana de configuracion, accedemos a "General Setup" y modificamos el nombre de la version local, despues seleccionamos "Preempt model" y lo establecemos en RT.

### Compilamos el Kernel
>make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs

### Carga en SD
Finalmente, debemos pasar a la tarjeta SD el Kernel y todos los archivos necesarios, para ello montamos en nuestro sistema la tarjeta (en este caso /dev/sdb1), utilizando los siguientes comandos,

>mkdir mnt  
>mkdir mnt/boot  
>mkdir mnt/root  
>sudo mount /dev/sdb1 mnt/boot  
>sudo mount /dev/sdb2 mnt/root  

instalamos los modulos del kernel

>sudo env PATH=$PATH make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH=mnt/root modules_install  

e instalamos los "Device Tree Blobs",

>sudo cp mnt/boot/$KERNEL.img mnt/boot/$KERNEL-backup.img  
>sudo cp arch/arm64/boot/Image mnt/boot/$KERNEL.img  
>sudo cp arch/arm64/boot/dts/broadcom/*.dtb mnt/boot/  
>sudo cp arch/arm64/boot/dts/overlays/*.dtb* mnt/boot/overlays/  
>sudo cp arch/arm64/boot/dts/overlays/README mnt/boot/overlays/  
>sudo umount mnt/boot  
>sudo umount mnt/root  
