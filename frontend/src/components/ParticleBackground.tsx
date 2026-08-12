import { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Grid } from '@react-three/drei';
import * as THREE from 'three';

const PARTICLE_COUNT = 600;
const BOX_SIZE = 20;

function Particles({ active }: { active: boolean }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const tempObject = new THREE.Object3D();

  const particlesData = useMemo(() => {
    const data = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const x = (Math.random() - 0.5) * BOX_SIZE;
      const y = (Math.random() - 0.5) * BOX_SIZE;
      const z = (Math.random() - 0.5) * BOX_SIZE;
      
      const velocity = new THREE.Vector3(
        (Math.random() - 0.5) * 0.2,
        (Math.random() - 0.5) * 0.2,
        (Math.random() - 0.5) * 0.2
      );
      
      data.push({ position: new THREE.Vector3(x, y, z), velocity });
    }
    return data;
  }, []);

  useFrame((state, delta) => {
    if (!meshRef.current) return;

    const speed = active ? 3.0 : 1.0;
    
    meshRef.current.rotation.y += delta * 0.05 * speed;

    particlesData.forEach((particle, i) => {
      particle.position.addScaledVector(particle.velocity, delta * speed);
      
      // Wrap particles around the box
      if (particle.position.x > BOX_SIZE / 2) particle.position.x = -BOX_SIZE / 2;
      if (particle.position.x < -BOX_SIZE / 2) particle.position.x = BOX_SIZE / 2;
      if (particle.position.y > BOX_SIZE / 2) particle.position.y = -BOX_SIZE / 2;
      if (particle.position.y < -BOX_SIZE / 2) particle.position.y = BOX_SIZE / 2;
      if (particle.position.z > BOX_SIZE / 2) particle.position.z = -BOX_SIZE / 2;
      if (particle.position.z < -BOX_SIZE / 2) particle.position.z = BOX_SIZE / 2;
      
      tempObject.position.copy(particle.position);
      tempObject.updateMatrix();
      meshRef.current!.setMatrixAt(i, tempObject.matrix);
    });
    
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, PARTICLE_COUNT]}>
      <sphereGeometry args={[0.03, 6, 6]} />
      <meshBasicMaterial color="#00d4ff" transparent opacity={0.6} />
    </instancedMesh>
  );
}

function EnergyRings({ active }: { active: boolean }) {
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const ring3Ref = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    const speed = active ? 2.5 : 1.0;
    if (ring1Ref.current) {
      ring1Ref.current.rotation.x += delta * 0.2 * speed;
      ring1Ref.current.rotation.y += delta * 0.1 * speed;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.y += delta * 0.15 * speed;
      ring2Ref.current.rotation.z += delta * 0.25 * speed;
    }
    if (ring3Ref.current) {
      ring3Ref.current.rotation.z -= delta * 0.2 * speed;
      ring3Ref.current.rotation.x -= delta * 0.15 * speed;
    }
  });

  const opacity = active ? 0.4 : 0.15;

  return (
    <group>
      <mesh ref={ring1Ref}>
        <torusGeometry args={[2, 0.01, 8, 64]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={opacity} />
      </mesh>
      <mesh ref={ring2Ref}>
        <torusGeometry args={[3, 0.01, 8, 64]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={opacity} />
      </mesh>
      <mesh ref={ring3Ref}>
        <torusGeometry args={[4, 0.01, 8, 64]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={opacity} />
      </mesh>
    </group>
  );
}

function CameraRig() {
  const { camera, mouse } = useThree();
  const vec = new THREE.Vector3();

  useFrame((state) => {
    const targetX = mouse.x * 0.3;
    const targetY = mouse.y * 0.3;
    
    camera.position.lerp(vec.set(targetX, 1 + targetY, 8), 0.05);
    camera.lookAt(0, 0, 0);
  });

  return null;
}

function GridOverlay() {
  const gridRef = useRef<THREE.Group>(null);
  
  useFrame((state, delta) => {
    if (gridRef.current) {
      gridRef.current.rotation.y += delta * 0.02;
    }
  });

  return (
    <group ref={gridRef} position={[0, -3, 0]}>
      <Grid 
        args={[100, 100]}
        cellSize={1} 
        cellThickness={0.5} 
        cellColor="#0a3d5c" 
        sectionSize={5} 
        sectionThickness={1} 
        sectionColor="#00d4ff" 
        fadeDistance={30} 
        fadeStrength={1} 
        infiniteGrid={true}
      />
    </group>
  );
}

export function ParticleBackground({ isProcessing }: { isProcessing?: boolean }) {
  return (
    <div className="particle-bg">
      <Canvas 
        dpr={[1, 1.5]} 
        gl={{ antialias: false, alpha: false }} 
        frameloop="always"
        camera={{ position: [0, 1, 8], fov: 60 }}
      >
        <color attach="background" args={['#020408']} />
        <fog attach="fog" args={['#020408', 5, 25]} />
        <CameraRig />
        <Particles active={!!isProcessing} />
        <GridOverlay />
        <EnergyRings active={!!isProcessing} />
      </Canvas>
    </div>
  );
}

export default ParticleBackground;
