<!DOCTYPE html>
<html lang="es">
    <head>
        <title>Pagina acceder</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            function login(){
                let username = document.getElementById("username").value;
                let password = document.getElementById("pwd").value;
                let message = document.getElementById("message");

                if (username == "" && password == ""){
                    message.innerText = "Debes cumplir con todos los campos";
                } else if (username == ""){
                    message.innerText = "Debes ingresar un nombre";
                } else if (password == "") {
                    message.innerText = "Debes ingresar una constraseña";
                } else {
                    message.innerText = "Ingresado! Saludos " + username + "!";
                }
            }
        </script>    
    </head>
    <body>
        <!-- Navbar -->
        <nav class="navbar bg-dark navbar-dark">
            <div class="container-fluid">
                <!-- Logo -->
                <a class="navbar-brand " href="index.php">Logo</a>    
            </div>         
        </nav>
        <!-- Pagina Login -->
        <div class="container mt-5">
            <div class="row justify-content-center">
                <form action="#">
                    <div class="mb-3 mt-3">
                        <label for="username" class="form-label">Nombre:</label>
                        <input type="text" class="form-control" id="username" placeholder="Ingresa un nombre" name="username">
                    </div>
                    <div class="mb-3">
                        <label for="pwd" class="form-label">Constraseña:</label>
                        <input type="password" class="form-control" id="pwd" placeholder="Ingresa una contraseña" name="pswd">
                    </div>
                    <div class="form-check mb-3">
                        <label class="form-check-label">
                        <input class="form-check-input" type="checkbox" name="remember"> Recordar
                        </label>
                    </div>
                    <button type="button" onclick="login();" class="btn btn-primary">Ingresar</button>
                </form>   
            </div>
            <!-- Mensaje login -->
            <p id="message" class="mt-3"></p>
        </div>
    </body>

</html>