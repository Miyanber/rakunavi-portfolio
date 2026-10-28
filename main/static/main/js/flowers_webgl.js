'use strict';
// WebGL2 rewrite of flowers.js (canvas 2D -> WebGL2 instanced sprites)
// 同じDOM構造とトリガー（#cow / #displayText / #toggle_filter_container）を維持。
// <script src=".../flowers_webgl.js" defer></script> に差し替えて使ってください。

(() => {
    // 初期化前に、articleがあればその大きさを保存
    const article = document.getElementById('window');
    if (article) {
        window.sessionStorage.setItem('article_width', article.clientWidth);
        window.sessionStorage.setItem('article_height', article.clientHeight);
        const rect = article.getBoundingClientRect();
        window.sessionStorage.setItem('article_top', rect.top);
        window.sessionStorage.setItem('article_left', rect.left);
    }

    const canvas = document.getElementById('scene');
    if (!canvas) return;
    /** @type {WebGL2RenderingContext} */
    const gl = canvas.getContext('webgl2', { alpha: true, antialias: true, premultipliedAlpha: false });
    if (!gl) {
        console.warn('WebGL2 not available; falling back to no-op');
        return;
    }

    // ========================= Config =========================
    const CONFIG = {
        baseCount: 50,
        upDraft: 0.04,
        windAmp: 3.3,
        windFreqX: 0.001,
        windFreqY: 0.001,
        turbulence: 0.1,
        petalMin: 12,
        petalMax: 22,
        depthMin: 0.6,
        depthMax: 1.0,
        notchDepth: 0.01,
        width: null,
        height: null,
    };

    // ========================= Canvas & DPI =========================
    let W = 0, H = 0, DPR = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    function resize() {
        DPR = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
        const width = CONFIG.width ?? innerWidth;
        const height = CONFIG.height ?? innerHeight;
        W = canvas.width = Math.floor(width * DPR);
        H = canvas.height = Math.floor(height * DPR);
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        gl.viewport(0, 0, W, H);
    }
    addEventListener('resize', resize, { passive: true });
    resize();

    // ========================= Utilities =========================
    const CENTER = () => ({ x: W * 0.5, y: H * 1.02 });
    const rand = (a, b) => a + Math.random() * (b - a);
    const randSign = () => (Math.random() < 0.5 ? -1 : 1);
    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

    function windField(x, y, t) {
        const nx = Math.sin((x + t * 800) * CONFIG.windFreqX);
        const ny = Math.cos((y + t * 900) * CONFIG.windFreqY);
        return { x: nx * CONFIG.windAmp, y: ny * CONFIG.windAmp * 0.5 };
    }

    const colorPresets = [
        [340, 100, 92], [335, 85, 90], [350, 95, 94],
        [330, 70, 88], [345, 100, 85], [338, 60, 91],
        [355, 90, 89], [328, 75, 87], [342, 100, 95],
        [333, 90, 86]
    ];

    // ========================= Shaders =========================
    const VS = `#version 300 es\n
  layout(location=0) in vec2 a_pos;              // quad verts in petal-local units
  layout(location=1) in vec2 i_translation;      // world px
  layout(location=2) in float i_rotation;        // radians
  layout(location=3) in float i_size;            // px (base scale)
  layout(location=4) in float i_depth;           // 0..1
  layout(location=5) in vec3  i_hsl;             // H,S,L
  layout(location=6) in float i_tilt;            // -0.5..0.5
  layout(location=7) in float i_flap;            // flap phase

  uniform vec2 u_resolution;                     // (W,H) in px

  out vec2 v_local;                              // local coords for SDF
  out float v_depth;
  out vec3 v_hsl;
  out float v_flap;                              // pass to fragment for subtle effects
  out float v_tilt;

  void main() {
    float flapScale = 1.0 + sin(i_flap) * 0.08;
    float angle = i_rotation + sin(i_flap) * 0.2 * i_tilt;
    float c = cos(angle);
    float s = sin(angle);
    mat2 rot = mat2(c, -s, s, c);

    // a_pos is already in petal-local units: x in [-1,1], y in [-1.3,0]
    vec2 local = rot * (a_pos * (i_size * flapScale));
    vec2 world = i_translation + local;

    // to clip space
    vec2 clip = (world / u_resolution * 2.0) - 1.0;
    clip.y = -clip.y; // canvas y-down to GL y-up

    gl_Position = vec4(clip, 0.0, 1.0);

    v_local = a_pos; // unscaled local coordinates for SDF
    v_depth = i_depth;
    v_hsl = i_hsl;
    v_flap = i_flap;
    v_tilt = i_tilt;
  }
  `;

    const FS = `#version 300 es\n
  precision highp float;
  in vec2 v_local;     // [-1,1] x [-1.3,0]
  in float v_depth;
  in vec3 v_hsl;       // H,S,L in degrees/percent
  in float v_flap;
  in float v_tilt;
  out vec4 outColor;

  // Petal SDF: leaf-like superellipse with a circular notch near the top
  float petalSDF(vec2 p, float notchDepth) {
    // p.x in [-1,1], p.y in [-1.3,0]
    float h = 1.3;
    float t = (p.y + h) / h; // 0 bottom, 1 top

    // width profile across height (wider around the middle)
    float halfW = mix(0.15, 1.0, pow(1.0 - t, 0.7));

    // superellipse boundary approximation
    float n = mix(2.0, 1.2, t);
    float m = 2.0;
    float dx = abs(p.x) / halfW;
    float dy = abs(p.y) / h;
    float f = pow(dx, n) + pow(dy, m) - 1.0; // inside <= 0

    // top notch (subtract circle)
    float notchY = -notchDepth * h * 0.5;
    float r = notchDepth * 0.6 * h;
    float notch = length(vec2(p.x, p.y - notchY)) - r; // inside < 0

    return max(f, -notch);
  }

  vec3 hsl2rgb(vec3 hsl) {
    float h = hsl.x / 360.0;
    float s = clamp(hsl.y / 100.0, 0.0, 1.0);
    float l = clamp(hsl.z / 100.0, 0.0, 1.0);
    float c = (1.0 - abs(2.0*l - 1.0)) * s;
    float x = c * (1.0 - abs(mod(h*6.0, 2.0) - 1.0));
    float m = l - 0.5 * c;
    vec3 rgb;
    if (h < 1.0/6.0) rgb = vec3(c, x, 0.0);
    else if (h < 2.0/6.0) rgb = vec3(x, c, 0.0);
    else if (h < 3.0/6.0) rgb = vec3(0.0, c, x);
    else if (h < 4.0/6.0) rgb = vec3(0.0, x, c);
    else if (h < 5.0/6.0) rgb = vec3(x, 0.0, c);
    else rgb = vec3(c, 0.0, x);
    return rgb + m;
  }

  void main() {
    float nd = 0.22; // notch depth (matches JS)
    float d = petalSDF(v_local, nd);
    float aa = fwidth(d);
    float alpha = smoothstep(0.0, -aa, d);
    if (alpha <= 0.001) discard;

    // vertical gradient (top slightly darker/shifted hue)
    float h = v_hsl.x;
    float s = v_hsl.y;
    float l = v_hsl.z;

    float y01 = clamp(-v_local.y / 1.3, 0.0, 1.0); // 0 bottom, 1 top
    vec3 colBase = hsl2rgb(vec3(h, s, l));
    vec3 colTop  = hsl2rgb(vec3(h - 6.0, clamp(s + 10.0, 0.0, 100.0), clamp(l - 12.0, 0.0, 100.0)));
    vec3 col = mix(colBase, colTop, y01);

    // subtle darkening by depth; gentle flicker via flap
    float shadow = 0.12 * v_depth;
    float flick = 0.02 * sin(v_flap * 2.0 + v_tilt * 3.14159);
    col *= (1.0 - shadow * 0.2 + flick);

    outColor = vec4(col, alpha * 0.95);
  }
  `;

    function compileShader(type, src) {
        const sh = gl.createShader(type);
        gl.shaderSource(sh, src);
        gl.compileShader(sh);
        if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
            console.error(gl.getShaderInfoLog(sh));
            gl.deleteShader(sh);
            return null;
        }
        return sh;
    }

    function createProgram(vsSrc, fsSrc) {
        const vs = compileShader(gl.VERTEX_SHADER, vsSrc);
        const fs = compileShader(gl.FRAGMENT_SHADER, fsSrc);
        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
            console.error(gl.getProgramInfoLog(prog));
            return null;
        }
        return prog;
    }

    const prog = createProgram(VS, FS);
    gl.useProgram(prog);

    const u_resolution = gl.getUniformLocation(prog, 'u_resolution');

    // ========================= Geometry (unit quad in petal-local) =========================
    // Quad covering x∈[-1,1], y∈[-1.3,0], two triangles
    const quad = new Float32Array([
        -1.0, -1.3, 1.0, -1.3, 1.0, 0.0,
        -1.0, -1.3, 1.0, 0.0, -1.0, 0.0,
    ]);
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const vboQuad = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vboQuad);
    gl.bufferData(gl.ARRAY_BUFFER, quad, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    // ========================= Instance Buffers =========================
    // Per-instance attributes: translation(2), rotation(1), size(1), depth(1), hsl(3), tilt(1), flap(1)
    const BYTES = Float32Array.BYTES_PER_ELEMENT;
    const components = [2, 1, 1, 1, 3, 1, 1];
    const offsets = [0, 2, 3, 4, 5, 8, 9]; // float offsets in the struct
    const strideFloats = 10; // total floats per instance

    const maxInstances = 500; // safety upper bound (auto-adjusted each frame)
    const instanceData = new Float32Array(strideFloats * maxInstances);
    const vboInst = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vboInst);
    gl.bufferData(gl.ARRAY_BUFFER, instanceData.byteLength, gl.DYNAMIC_DRAW);

    // Bind attributes with divisors
    let attribLoc = 1;
    for (let i = 0; i < components.length; i++) {
        const size = components[i];
        gl.enableVertexAttribArray(attribLoc);
        gl.vertexAttribPointer(attribLoc, size, gl.FLOAT, false, strideFloats * BYTES, offsets[i] * BYTES);
        gl.vertexAttribDivisor(attribLoc, 1);
        attribLoc++;
    }

    gl.bindVertexArray(null);

    // ========================= Petal model (CPU sim, GPU draw) =========================
    class Petal {
        constructor(spawnX, spawnY) { this.reset(spawnX, spawnY); }
        reset(spawnX, spawnY) {
            const d = rand(CONFIG.depthMin, CONFIG.depthMax);
            this.d = d;
            this.size = rand(CONFIG.petalMin, CONFIG.petalMax) * d * DPR;
            this.x = spawnX + rand(-20, 20) * DPR;
            this.y = spawnY + rand(-10, 10) * DPR;
            this.vx = rand(-1.5, 1.5) * d;
            this.vy = -rand(1.0, 2.0) * d;
            this.rot = rand(0, Math.PI * 2);
            this.rotV = rand(0.002, 0.01) * randSign();
            this.tilt = rand(-0.5, 0.5);
            this.flapT = rand(0, Math.PI * 2);
            const c = colorPresets[(Math.random() * colorPresets.length) | 0];
            this.h = c[0]; this.s = c[1]; this.l = c[2];
        }
        step(dt, t, center) {
            const wind = windField(this.x, this.y, t);
            this.vx += wind.x * dt;
            this.vy += wind.y * dt;
            this.vy -= CONFIG.upDraft * this.d * dt * 60;
            this.vx += (Math.random() - 0.5) * CONFIG.turbulence * this.d;
            this.vy += (Math.random() - 0.5) * CONFIG.turbulence * this.d;
            this.x += this.vx * dt * 60;
            this.y += this.vy * dt * 60;
            this.rot += this.rotV;
            this.flapT += 0.07 + 0.03 * this.d;
            if (this.y < -80 * DPR || this.x < -80 * DPR || this.x > W + 80 * DPR) {
                this.reset(center.x, center.y);
            }
        }
    }

    const petals = [];
    let running = false;

    function desiredCount() {
        const base = CONFIG.baseCount;
        const k = (W * H) / (1280 * 720 * DPR * DPR);
        return Math.floor(base * clamp(k, 0.6, 2.0));
    }
    function spawn(n, center) {
        for (let i = 0; i < n; i++) petals.push(new Petal(center.x, center.y));
    }

    function startConfetti(options = {}) {

        Object.assign(CONFIG, options);

        resize();

        if (!running) {
            running = true;
            spawn(desiredCount(), CENTER());
            last = performance.now();
            requestAnimationFrame(loop);
        }
    }

    // ========================= Render Loop =========================
    gl.enable(gl.BLEND);
    gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    let last = performance.now();
    function loop(now) {
        if (!running) return;
        const dt = Math.min(0.033, (now - last) / 1000);
        last = now;

        gl.viewport(0, 0, W, H);
        gl.clearColor(0, 0, 0, 0); // transparent
        gl.clear(gl.COLOR_BUFFER_BIT);

        const t = now / 1000;
        const center = CENTER();
        const need = desiredCount();
        if (petals.length < need) spawn(need - petals.length, center);
        else if (petals.length > need) petals.splice(need);

        // depth sort (back to front, lower d first)
        petals.sort((a, b) => a.d - b.d);

        // Simulate and pack instance data
        const N = petals.length;
        let ptr = 0;
        for (let i = 0; i < N; i++) {
            const p = petals[i];
            p.step(dt, t, center);
            // translation
            instanceData[ptr++] = p.x; // i_translation.x
            instanceData[ptr++] = p.y; // i_translation.y
            // rotation
            instanceData[ptr++] = p.rot; // i_rotation
            // size
            instanceData[ptr++] = p.size; // i_size
            // depth
            instanceData[ptr++] = p.d; // i_depth
            // hsl
            instanceData[ptr++] = p.h; // i_hsl.x
            instanceData[ptr++] = p.s; // i_hsl.y
            instanceData[ptr++] = p.l; // i_hsl.z
            // tilt
            instanceData[ptr++] = p.tilt; // i_tilt
            // flap
            instanceData[ptr++] = p.flapT; // i_flap
        }

        // Upload instance buffer (only the used portion)
        gl.bindBuffer(gl.ARRAY_BUFFER, vboInst);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, instanceData.subarray(0, ptr));

        // Draw
        gl.useProgram(prog);
        gl.uniform2f(u_resolution, W, H);

        gl.bindVertexArray(vao);
        gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, N);
        gl.bindVertexArray(null);

        requestAnimationFrame(loop);
    }

    // ========================= Trigger wiring (unchanged UX) =========================
    const inputElement = document.getElementById('cow');
    const displayText = document.getElementById('displayText');
    if (inputElement && displayText) {
        inputElement.addEventListener('input', function () {
            const inputValue = inputElement.value;
            if (inputValue.trim() !== '') {
                displayText.textContent = '> ' + inputValue;
                if (~inputValue.indexOf('secret')) {
                    displayText.textContent = '我々は秘密主義ではありません。';
                } else if (inputValue === 'python') {
                    displayText.textContent = '正解!!我々はDjangoを使用しています。';
                    inputElement.disabled = true;
                    startConfetti();
                    const tgl = document.getElementById('toggle_filter_container');
                    if (tgl) tgl.style.display = 'block';
                } else if (inputValue === 'javascript') {
                    displayText.textContent = '惜しい。実は、4番目なんです。';
                } else if (inputValue === 'php') {
                    displayText.textContent = '違います。';
                } else if (inputValue === 'shell') {
                    displayText.textContent = '違います。しかしLinuxは大好きです。';
                }
            } else {
                displayText.textContent = 'ヒント：　2位がHTML、3位がCSS';
            }
        });
    }

    // ========================= Special effect toggle (PM hook維持) =========================
    const toggleButton = document.getElementById('toggle_filter');
    if (toggleButton) {
        toggleButton.addEventListener('click', function () {
            if (document.body.classList.contains('haru')) {
                document.body.classList.remove('haru');
                if (typeof window.stopProjectionMapping === 'function') window.stopProjectionMapping();
            } else {
                document.body.classList.add('haru');
                if (typeof window.startProjectionMapping === 'function') {
                    window.startProjectionMapping({ projectorCount: 6, flickerMin: 0.5, flickerMax: 1.0 });
                }
            }
        });
    }

    // 利用可能にする
    window.startFlowerEffect = startConfetti;

})();
