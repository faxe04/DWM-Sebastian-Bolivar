workspace "Aroma & Café" "Backend académico de cafetería" {
    model {
        customer = person "Cliente" "Consulta catálogo y compra"
        admin = person "Administrador" "Gestiona usuarios, caja y despacho"
        cafeteria = softwareSystem "Aroma & Café" {
            gateway = container "API Gateway" "Rutas, identidad, límites y trazabilidad" "FastAPI"
            auth = container "Auth" "Cuentas y sesiones" "FastAPI"
            inventory = container "Inventory" "Productos y reservas" "FastAPI"
            clients = container "Clients" "Perfiles y correo dummy" "FastAPI"
            orders = container "Orders" "Pedidos, caja, boletas y despacho" "FastAPI"
            payments = container "Payments" "Pago y reembolso dummy" "FastAPI"
            graphql = container "GraphQL" "Agregación privada" "Apollo y Express"
            mysql = container "Persistencia" "Cinco bases y cinco usuarios separados" "MySQL" {
                tags "Database"
            }
            vault = container "Secretos" "KV v2, política de lectura del gateway" "Vault"
        }
        customer -> gateway "Consulta y compra" "HTTPS local"
        admin -> gateway "Administra" "HTTPS local"
        gateway -> auth "Introspección y usuarios" "HTTP privado"
        gateway -> inventory "Catálogo y gestión" "HTTP privado"
        gateway -> clients "Perfiles" "HTTP privado"
        gateway -> orders "Pedidos, caja y documentos" "HTTP privado"
        gateway -> payments "Pagos" "HTTP privado"
        gateway -> graphql "Consultas agregadas" "HTTP privado"
        gateway -> vault "Lee referencias de integración" "HTTP privado"
        graphql -> orders "Pedido autorizado"
        graphql -> clients "Perfil autorizado"
        graphql -> payments "Estado del pago"
        graphql -> inventory "Catálogo"
        orders -> inventory "Reserva y libera stock"
        orders -> clients "Comprueba perfil y encola boleta"
        orders -> payments "Bloquea pago y reembolsa"
        payments -> orders "Confirma pago"
        clients -> auth "Verifica cuenta para registro asistido"
        auth -> mysql "Base auth"
        inventory -> mysql "Base inventory"
        clients -> mysql "Base clients"
        orders -> mysql "Base orders"
        payments -> mysql "Base payments"
        deploymentEnvironment "Local" {
            deploymentNode "Equipo del alumno" "Docker Desktop" {
                deploymentNode "Red privada de Compose" {
                    containerInstance auth
                    containerInstance inventory
                    containerInstance clients
                    containerInstance orders
                    containerInstance payments
                    containerInstance graphql
                    containerInstance mysql
                    containerInstance vault
                }
                deploymentNode "Entrada local 8000" {
                    containerInstance gateway
                }
            }
        }
    }
    views {
        systemContext cafeteria "context" {
            include *
            autolayout lr
        }
        container cafeteria "containers" {
            include *
            autolayout lr
        }
        deployment cafeteria "Local" "deployment" {
            include *
            autolayout lr
        }
        styles {
            element "Database" {
                shape Cylinder
            }
        }
    }
}
