/**
 * SVG twin of the composite shader's `sketch()`: the image sinks to a dark plate and its
 * Sobel contours glow warm white. SVG convolutions clamp negatives, so each gradient
 * direction is taken separately and summed.
 */
export function UnderdrawingFilter() {
  return (
    <svg className="svg-defs" width="0" height="0" aria-hidden="true" focusable="false">
      <filter id="underdrawing" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
        <feColorMatrix in="SourceGraphic" type="saturate" values="0" result="gray" />
        <feGaussianBlur in="gray" stdDeviation="0.6" result="soft" />
        <feConvolveMatrix in="soft" order="3" kernelMatrix="-1 0 1 -2 0 2 -1 0 1" preserveAlpha="true" result="gx1" />
        <feConvolveMatrix in="soft" order="3" kernelMatrix="1 0 -1 2 0 -2 1 0 -1" preserveAlpha="true" result="gx2" />
        <feConvolveMatrix in="soft" order="3" kernelMatrix="-1 -2 -1 0 0 0 1 2 1" preserveAlpha="true" result="gy1" />
        <feConvolveMatrix in="soft" order="3" kernelMatrix="1 2 1 0 0 0 -1 -2 -1" preserveAlpha="true" result="gy2" />
        <feComposite in="gx1" in2="gx2" operator="arithmetic" k2="1" k3="1" result="gx" />
        <feComposite in="gy1" in2="gy2" operator="arithmetic" k2="1" k3="1" result="gy" />
        <feComposite in="gx" in2="gy" operator="arithmetic" k2="1" k3="1" result="edge" />
        <feColorMatrix
          in="edge"
          type="matrix"
          values="2.5 0 0 0 -0.13  2.3 0 0 0 -0.12  2.0 0 0 0 -0.11  0 0 0 0 1"
          result="ink"
        />
        <feColorMatrix
          in="SourceGraphic"
          type="matrix"
          values="0.14 0 0 0 0.012  0 0.14 0 0 0.014  0 0 0.14 0 0.026  0 0 0 1 0"
          result="plate"
        />
        <feBlend in="ink" in2="plate" mode="screen" />
      </filter>
      <filter id="ragged" x="-10%" y="-10%" width="120%" height="120%">
        <feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="2" seed="7" result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale="9" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </svg>
  )
}
