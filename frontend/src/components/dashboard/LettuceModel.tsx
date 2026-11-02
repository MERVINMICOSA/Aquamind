import { Suspense, useEffect, useMemo, useRef } from 'react'
import { Canvas, useFrame, useLoader } from '@react-three/fiber'
import {
  Box3,
  Group,
  Mesh,
  MeshStandardMaterial,
  Object3D,
  SRGBColorSpace,
  Texture,
  Vector3,
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

import lettuceModelUrl from '../../assets/dashboard/lettuce.glb?url'


function LettuceScene() {
  const rotationGroup = useRef<Group>(null)
  const gltf = useLoader(GLTFLoader, lettuceModelUrl)

  const model = useMemo(() => {
    const clone = gltf.scene.clone(true)

    const bounds = new Box3().setFromObject(clone)
    const size = bounds.getSize(new Vector3())
    const center = bounds.getCenter(new Vector3())

    const largestDimension = Math.max(
      size.x,
      size.y,
      size.z,
    )

    const targetSize = 2.8
    const scale =
      largestDimension > 0
        ? targetSize / largestDimension
        : 1

    clone.position.set(
      -center.x,
      -center.y,
      -center.z,
    )

    clone.scale.setScalar(scale)

    clone.traverse((object: Object3D) => {
      if (!(object instanceof Mesh)) {
        return
      }

      object.castShadow = true
      object.receiveShadow = true

      const materials = Array.isArray(object.material)
        ? object.material
        : [object.material]

      materials.forEach((material) => {
        if (!(material instanceof MeshStandardMaterial)) {
          return
        }

        const maps: Array<Texture | null> = [
          material.map,
          material.emissiveMap,
        ]

        maps.forEach((texture) => {
          if (texture) {
            texture.colorSpace = SRGBColorSpace
          }
        })

        material.needsUpdate = true
      })
    })

    return clone
  }, [gltf.scene])

  useEffect(() => {
    const mediaQuery = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    )

    const updateMotionPreference = () => {
      if (rotationGroup.current) {
        rotationGroup.current.userData.reduceMotion =
          mediaQuery.matches
      }
    }

    updateMotionPreference()

    mediaQuery.addEventListener(
      'change',
      updateMotionPreference,
    )

    return () => {
      mediaQuery.removeEventListener(
        'change',
        updateMotionPreference,
      )
    }
  }, [])

  useFrame((_, delta) => {
    const group = rotationGroup.current

    if (
      !group ||
      group.userData.reduceMotion
    ) {
      return
    }

    group.rotation.y += delta * 0.28
  })

  return (
    <group
      ref={rotationGroup}
      position={[0, 0.08, 0]}
    >
      <primitive object={model} />
    </group>
  )
}


export function LettuceModel() {
  return (
    <div className="lettuce-model">
      <Canvas
        className="lettuce-model__canvas"
        camera={{
          position: [0, 0.2, 4.6],
          fov: 40,
        }}
        dpr={[1, 1.5]}
        gl={{
          alpha: true,
          antialias: true,
        }}
      >
        <ambientLight intensity={1.4} />

        <directionalLight
          position={[3, 4, 5]}
          intensity={2.2}
        />

        <directionalLight
          position={[-3, 1, 2]}
          intensity={1}
        />

        <Suspense fallback={null}>
          <LettuceScene />
        </Suspense>
      </Canvas>
    </div>
  )
}