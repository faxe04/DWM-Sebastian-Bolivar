<!DOCTYPE html>
<html lang="es">
    <head>
        <title>Pagina principal</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>     
    </head>
    <body>
        <!-- Navbar -->
        <nav class="navbar bg-dark navbar-dark">
            <div class="container-fluid">
                <div class="d-flex align-items-center">
                    <button class="navbar-toggler me-3" type="button" data-bs-toggle="offcanvas" data-bs-target="#lateralMenu">
                        <span class="navbar-toggler-icon"></span>
                    </button>
                    <!-- Logo -->
                    <a class="navbar-brand " href="index.php">Logo</a>
                </div>
                <form class="d-flex">
                    <input class="form-control me-2" type="text" placeholder="Search">
                    <button class="btn btn-primary" type="button">Search</button>
                </form>
                <a class="btn btn-outline-primary" href="login.php">Acceder</a>
        </nav>
        <!-- Menu Lateral -->
        <div class="offcanvas offcanvas-start bg-dark text-white" tabindex="-1" id="lateralMenu">
            <div class="offcanvas-header">
                <h5 class="offcanvas-title">Menu</h5>
                <button class="btn-close btn-close-white" type="button" data-bs-dismiss="offcanvas"></button>
            </div>
            <li class="p-2">
                <p><a class="text-decoration-none text-white" href="index.php">Home</a></p>
                <p><a class="text-decoration-none text-white" href="channel.php">Canal</a></p>
                <p><a class="text-decoration-none text-white" href="video.php">Video</a></p>
                <p><a class="text-decoration-none text-white" href="login.php">Acceder</a></p>
            </li>
        </div>
        <!-- Pagina principal -->
        <div class="row g-4 p-4">
            <div class="col-12 col-sm-6 col-md-4 col-lg-3">
                <div class="card h-100">
                    <a href="video.php">
                        <img class="card-img-top" src="img/thumbnail.jpg" alt="Video">
                    </a>
                    <div class="card-body">
                        <h5 class="card-title">
                            <a href="video.php" class="text-decoration-none text-dark">Titulo 1</a>
                        </h5>
                        <p class="card-text mb-1">
                            <a href="channel.php" class="text-decoration-none text-muted">Nombre canal</a>
                        </p>
                        <p class="card-text text-muted">visitas</p>
                    </div>
                </div>
            </div>
            <div class="col-12 col-sm-6 col-md-4 col-lg-3">
                <div class="card h-100">
                    <a href="video.php">
                        <img class="card-img-top"src="img/thumbnail.jpg"alt="Video">
                    </a>
                    <div class="card-body">
                        <h5 class="card-title">
                            <a href="video.php" class="text-decoration-none text-dark">Titulo 2</a>
                        </h5>
                        <p class="card-text mb-1">
                            <a href="channel.php" class="text-decoration-none text-muted">Nombre canal</a>
                        </p>
                        <p class="card-text text-muted">visitas</p>
                    </div>
                </div>
            </div>
            <div class="col-12 col-sm-6 col-md-4 col-lg-3">
                <div class="card h-100">
                    <a href="video.php">
                        <img class="card-img-top" src="img/thumbnail.jpg" alt="Video">
                    </a>
                    <div class="card-body">
                        <h5 class="card-title">
                            <a href="video.php" class="text-decoration-none text-dark">Titulo 3</a>
                        </h5>
                        <p class="card-text mb-1">
                            <a href="channel.php" class="text-decoration-none text-muted">Nombre canal</a>
                        </p>
                        <p class="card-text text-muted">visitas</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
</html>