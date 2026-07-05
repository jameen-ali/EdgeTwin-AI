import { NodeIO } from '@gltf-transform/core';
import { KHRONOS_EXTENSIONS } from '@gltf-transform/extensions';
import fs from 'fs';

async function main() {
    const io = new NodeIO().registerExtensions(KHRONOS_EXTENSIONS);
    const glbPath = 'd:/COLLEGE/HACKATHON/Prototype/TATA/frontend/public/models/white_mesh.glb';
    
    // Read the document
    const document = await io.read(glbPath);
    
    // Create a new premium material
    const premiumMaterial = document.createMaterial('PremiumWhite')
        .setBaseColorFactor([0.92, 0.94, 0.96, 1.0]) // Cool, bright titanium white
        .setMetallicFactor(0.85)
        .setRoughnessFactor(0.15);
        
    // Add clearcoat extension
    const clearcoatExtension = document.createExtension(KHRONOS_EXTENSIONS.find(e => e.EXTENSION_NAME === 'KHR_materials_clearcoat'));
    if (clearcoatExtension) {
        const clearcoat = clearcoatExtension.createClearcoat()
            .setClearcoatFactor(1.0)
            .setClearcoatRoughnessFactor(0.05);
        premiumMaterial.setExtension('KHR_materials_clearcoat', clearcoat);
        console.log(`- Configured Clearcoat extension for premium material`);
    }

    // Assign to all meshes
    const meshes = document.getRoot().listMeshes();
    console.log(`Found ${meshes.length} meshes.`);
    let primitivesUpdated = 0;
    
    for (const mesh of meshes) {
        for (const prim of mesh.listPrimitives()) {
            prim.setMaterial(premiumMaterial);
            primitivesUpdated++;
        }
    }
    
    console.log(`Assigned premium material to ${primitivesUpdated} primitives.`);
    
    // Save the upgraded document back to the same path
    await io.write(glbPath, document);
    console.log('Successfully upgraded GLB materials and saved to:', glbPath);
}

main().catch(console.error);
