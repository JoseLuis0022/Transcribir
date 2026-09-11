// Aplica transcribir/AppIcon.icns como ícono visible en Finder a las rutas indicadas.
// Uso: swift scripts/aplicar_icono.swift <icns> <ruta> [<ruta> ...]
import AppKit

let args = CommandLine.arguments
guard args.count >= 3, let icono = NSImage(contentsOfFile: args[1]) else {
    print("Uso: swift aplicar_icono.swift <icns> <ruta>...")
    exit(1)
}
for ruta in args.dropFirst(2) {
    let ok = NSWorkspace.shared.setIcon(icono, forFile: ruta, options: [])
    print(ok ? "Ícono aplicado: \(ruta)" : "No se pudo aplicar: \(ruta)")
}
