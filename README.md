# CRT

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
>make menuconfig

Dentro de la ventana de configuracion, accedemos a "General Setup" y modificamos el nombre de la version local, despues seleccionamos "Preempt model" y lo establecemos en RT.

### Compilamos el Kernel
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image modules dtbs
