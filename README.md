# CRT
## Introducción
Este repositorio describe el proyecto realizado para la asignatura "Control mediante Real-Time Linux". En este proyecto se utiliza una Raspberry Pi 4B de 8GB de RAM para implementar una aplicacion en tiempo real. La aplicación a implementar se trata de un programa que incrementa y decrementa en tiempo real un contador en función de los pulsos detectados en dos pares de fototransistores, el valor del contador se muestra en una pantalla OLED de 0,96" controlada mediante i2c. Adicionalmente, hay un botón que simula una parada de emergencia y cuya única función es encender un LED rojo.

## Descripción del sistema
El proyecto está compuesto por varios archivos Python, cada uno con funciones específicas. Estos, se relacionan entre sí mediante el uso compartido de recursos como colas (Queue)
y variables de estado (Value). La interacción con el hadware se realiza a través de la biblioteca gpiozero y la visualización OLED mediante la librería luma.oled.

El archivo main.py es el script principal, donde se inicializan los sensores, el LED rojo, el botón y la pantalla OLED. En este archivo, se crea el objeto que maneja el contador, que lleva
la cuenta de los eventos. Adenás, también se configuran las interrupciones, así cuando un sensor detecta un cambio se llama a la función que actualiza el contador. 
Por otro lado, también se lanza un proceso aparta para encargarse de actualizar la pantalla, de modo que esta esté leyendo continuamente el valor del contador sin molestar al resto del sistema.
Finalmente, es importante comentar la gestión de prioridades de los procesos de este archivo. El proceso que enciende el LED rojo por una emergencia es el que mayor prioridad tiene (90), ya que
en caso de emergencia es esencial que todo quede en segundo plano menos la señal de emergencia que es el LED rojo. Sin embargo, la pantalla baja tiene una prioridad más baja (20), porque no es
tan crítico como puede ser la señal de emergencia.

En el archivo ContadorLocal.py se gestiona el valor del contador con dos métodos: incrementar() y decrementar(). Estos están protegidos por un bloqueo para evitar que dos procesos accedan al
contador al mismo tiempo y así evitar errores que se podrían generar. Cada vez que se actualiza el valor del contador, se manda a la Queue que está leyendo continuamente le proceso de la pantalla
OLED, así todos los cambios se reflejan al momento.

El archivo shared_resources.py solamente define el Queue que se utiliza como recurso compartido entre procesos. Se define la Queue aquí para que todos los módulos que la necesiten la importen
desde un único lugar.

Finalmente, tasks.py contiene las funciones que hacen tareas concretas. Las funciones increment_callback() y decrement_callback() se ejecutan cuando los sensores detectan una interrupción.
Verifican que no haya múltiples disparos por ruido con el sistema debounce y actualizan el contador si el sistema está activo. Asimismo, button_callback() se ejecuta cuando se pulsa el botón físico.
Si no hay una emergencia activa, se lanza un proceso que enciende el LED rojo durante un segundo a modo de emergencia. Como se ha comento antes, este proceso tiene prioridad alta para que la
emergencia se active con máxima prioridad. Por otro lado, tarea_oled() es el proceso que se encarga de leer el Queue y actualiza la pantalla OLED con el valor del contador. Esta función 
está en un bucle que se repite constantemente. Por último, la función set_priority() ajusta la prioridad de ejecución de los procesos, usando las capacidades real-time del sistema. Si no se
tienen pemisos de superusuario, se muestra un aviso.

## Kernel
Para poder realzar aplicaciones en tiempo real se instala un Kernel en tiempo real que nos permitirá utilizar un scheduler diferente, a continuación se explica el procedimiento llevado a cabo para descargar el código fuente del Kernel, configurarlo y compilarlo.  

### Descarga del Kernel y el parche
Accedemos a la documentación oficial de Raspberry Pi mediante el siguiente link:
https://www.raspberrypi.com/documentation/computers/linux_kernel.html

Descarga del codigo fuente desde el repositorio oficial:
>git clone --depth=1 https://github.com/raspberrypi/linux

Descargamos y aplicammos el parche de tiempo real obtenido mediante:
>wget https://www.kernel.org/pub/linux/kernel/projects/rt/6.6/patch-6.6.77-rt50.patch.gz

Descomprimimos el fichero usando:
>gunzip patch-6.6.77-rt50.patch

Lo movemos al interior de la carpeta linux y parcheamos mediante el siguiente comando.

### Aplicamos el parche
>patch -p1 < patch-6.6.77-rt50.patch

### Configuración y compilación del Kernel
Configuramos el Kernel para nuestra Raspberry Pi 4B de 64 bits
>cd linux  
>KERNEL=kernel8  
>make bcm2711_defconfig

Configuramos las opciones del Kernel utilizando:
>make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- menuconfig

Dentro de la ventana de configuracion, accedemos a "General Setup" y modificamos el nombre de la versión local, despues seleccionamos "Preempt model" y lo establecemos en RT.

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
