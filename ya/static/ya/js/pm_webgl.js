/* pm_webgl.js — WebGL2 Projection Mapping (drop-in replacement)
   API: startProjectionMapping(options), stopProjectionMapping()
   options: { opacity=1.0, projectorCount=5, flickerMin=0.4, flickerMax=1.0 }
*/

(() => {
    const MAX_P = 32; // 安全上限（必要なら増やせる）。options.projectorCount <= MAX_P を想定。
    const _pmState = {
        running: false,
        canvas: null,
        gl: null,
        prog: null,
        vao: null,
        u: {},
        requestId: null,
        DPR: 1,
        W: 0, H: 0,
        pointer: { x: 0.5, y: 0.5, active: false },
        projectors: [],
        flickerMin: 0.4,
        flickerMax: 1.0,
        startTime: 0,
    };

    // =============== Public API =================
    window.startProjectionMapping = function startProjectionMapping(options = {}) {
        if (_pmState.running) return;
        _pmState.running = true;

        const {
            opacity = 1.0,
            projectorCount = 5,
            flickerMin = 0.4,
            flickerMax = 1.0,
        } = options;

        _pmState.flickerMin = flickerMin;
        _pmState.flickerMax = flickerMax;

        const canvas = document.getElementById('pm-overlay');
        if (!canvas) {
            console.warn('[pm_webgl] #pm-overlay が見つかりません。');
            _pmState.running = false;
            return;
        }

        // Canvasスタイルは従来互換
        canvas.style.cssText = `
      position:fixed;
      inset:0;
      z-index:9998;
      pointer-events:none;
      mix-blend-mode:screen;
      opacity:${opacity};
    `;

        // WebGL2 context
        const gl = canvas.getContext('webgl2', { alpha: true, antialias: true, premultipliedAlpha: true });
        if (!gl) {
            console.warn('[pm_webgl] WebGL2 が利用できません。');
            _pmState.running = false;
            return;
        }

        _pmState.canvas = canvas;
        _pmState.gl = gl;

        // DPI & リサイズ
        function resize() {
            _pmState.DPR = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
            _pmState.W = canvas.width = Math.floor(innerWidth * _pmState.DPR);
            _pmState.H = canvas.height = Math.floor(innerHeight * _pmState.DPR);
            canvas.style.width = innerWidth + 'px';
            canvas.style.height = innerHeight + 'px';
            gl.viewport(0, 0, _pmState.W, _pmState.H);
        }
        addEventListener('resize', resize, { passive: true });
        resize();

        // 入力（ポインター）
        const updatePointer = (clientX, clientY) => {
            const rect = canvas.getBoundingClientRect();
            _pmState.pointer.x = (clientX - rect.left) / rect.width;
            _pmState.pointer.y = (clientY - rect.top) / rect.height;
            _pmState.pointer.active = true;
        };
        window.addEventListener('mousemove', e => updatePointer(e.clientX, e.clientY), { passive: true });
        window.addEventListener('touchmove', e => {
            const t = e.touches && e.touches[0];
            if (t) updatePointer(t.clientX, t.clientY);
        }, { passive: true });
        window.addEventListener('mouseleave', () => { _pmState.pointer.active = false; }, { passive: true });

        // プロジェクタ初期化
        const n = Math.min(Math.max(1, projectorCount | 0), MAX_P);
        _pmState.projectors = new Array(n).fill(null).map(() => ({
            x: Math.random(), y: Math.random(),
            vx: (Math.random() * 0.15 + 0.05) * (Math.random() < 0.5 ? -1 : 1),
            vy: (Math.random() * 0.15 + 0.05) * (Math.random() < 0.5 ? -1 : 1),
            r: 0.18 + Math.random() * 0.22,
            hue: Math.random() * 360,
            phase: Math.random() * Math.PI * 2,
            flickerSpeed: 0.5 + Math.random() * 1.5,
            flickerPhase: Math.random() * Math.PI * 2
        }));

        // GLセットアップ
        setupGL();
        _pmState.startTime = performance.now();
        _pmState.requestId = requestAnimationFrame(loop);
    };

    window.stopProjectionMapping = function stopProjectionMapping() {
        if (!_pmState.running) return;
        _pmState.running = false;
        if (_pmState.requestId) cancelAnimationFrame(_pmState.requestId);
        const { gl, canvas } = _pmState;
        if (gl && canvas) {
            gl.bindFramebuffer(gl.FRAMEBUFFER, null);
            gl.clearColor(0, 0, 0, 0);
            gl.clear(gl.COLOR_BUFFER_BIT);
        }
    };

    // =============== GL Pipeline =================
    function setupGL() {
        const { gl } = _pmState;

        // Fullscreen triangle (gl_VertexID trick)
        const vao = gl.createVertexArray();
        gl.bindVertexArray(vao);

        const vs = `#version 300 es
    out vec2 v_uv;
    void main() {
      // 3-vertex fullscreen triangle
      vec2 pos = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
      v_uv = pos;
      gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
    }`;

        const fs = `#version 300 es
    precision highp float;
    in vec2 v_uv;
    out vec4 outColor;

    uniform float u_time;
    uniform vec2  u_res;        // (W, H)
    uniform int   u_count;      // projector count
    uniform float u_flickerMin;
    uniform float u_flickerMax;
    uniform vec2  u_pointer;    // [0..1]
    uniform int   u_pointerActive;

    // packed arrays (length MAX_P)
    // A: pos.xy (0..1), radiusNorm.z (0..1 relative to min(res.x,res.y)), unused.w
    uniform vec4  u_projA[${MAX_P}];
    // B: hue (deg), phase, flickerSpeed, flickerPhase
    uniform vec4  u_projB[${MAX_P}];

    // === Helpers ===
    float sat(float x){ return clamp(x,0.0,1.0); }

    // hsv/hsl helpers (H in degrees)
    vec3 hsl2rgb(vec3 hsl){
      float h = hsl.x / 360.0;
      float s = sat(hsl.y/100.0);
      float l = sat(hsl.z/100.0);
      float c = (1.0 - abs(2.0*l - 1.0)) * s;
      float x = c * (1.0 - abs(mod(h*6.0, 2.0) - 1.0));
      float m = l - 0.5*c;
      vec3 rgb;
      if      (h < 1.0/6.0) rgb = vec3(c, x, 0.0);
      else if (h < 2.0/6.0) rgb = vec3(x, c, 0.0);
      else if (h < 3.0/6.0) rgb = vec3(0.0, c, x);
      else if (h < 4.0/6.0) rgb = vec3(0.0, x, c);
      else if (h < 5.0/6.0) rgb = vec3(x, 0.0, c);
      else                   rgb = vec3(c, 0.0, x);
      return rgb + m;
    }

    // simple hash noise (grain)
    float hash(vec2 p){
      // IQ-style hash
      p = vec2( dot(p, vec2(127.1,311.7)),
                dot(p, vec2(269.5,183.3)) );
      return fract(sin(p.x+p.y) * 43758.5453123);
    }

    void main(){
      vec2 res = u_res;
      vec2 uv = v_uv;               // [0,1]
      vec2 frag = uv * res;

      // --- Background fade (very subtle persistence) ---
      // 前フレームの情報は参照できないので、見た目上の薄いベールのみ
      vec3 col = vec3(0.0);

      // --- Projectors (additive-like) ---
      float minWH = min(res.x, res.y);
      for (int i=0; i<${MAX_P}; i++){
        if (i >= u_count) break;
        vec4 A = u_projA[i];
        vec4 B = u_projB[i];
        vec2 ppos = A.xy * res;
        float R = A.z * minWH; // base radius

        float pulse = sin(u_time * 1.5 + B.y) * 0.08;
        float r = R * (1.0 + pulse);

        float d = distance(frag, ppos)/max(r,1.0);
        float v = smoothstep(1.0, 0.0, d); // 0 at edge -> 1 center

        float flick = (sin(B.z * u_time + B.w) + 1.0) * 0.5; // 0..1
        float bright = mix(u_flickerMin, u_flickerMax, flick);

        // radial falloff shaping
        float core = pow(v, 1.2);
        float mid  = pow(v, 2.2) * 0.7;
        float edge = pow(v, 6.0) * 0.35;
        float amp = (core + mid + edge) * bright;

        // hue-based coloring (S,L は固定め)
        vec3 rgb = hsl2rgb(vec3(B.x, 95.0, 72.0));
        col += rgb * amp;
      }

      // --- Pointer spotlight ---
      if (u_pointerActive == 1){
        vec2 p = u_pointer * res;
        float R = min(res.x, res.y) * 0.35;
        float v = 1.0 - sat(distance(frag, p)/R);
        float ring = smoothstep(0.0, 1.0, v);
        vec3 white = vec3(1.0);
        col += white * (ring * 0.9 + pow(ring, 4.0) * 0.4);
      }

      // --- Scanline band ---
      float bandY = mod(u_time * 0.03 * res.y * 2.0, res.y * 2.0) - res.y;
      float bandH = max(80.0, res.y * 0.12);
      float gy = sat((frag.y - bandY)/bandH);
      float band = smoothstep(0.0, 0.5, gy) * (1.0 - smoothstep(0.5, 1.0, gy));
      col += vec3(band) * 0.18;

      // --- Grain (procedural, time varying) ---
      float g = hash(frag * 0.75 + u_time*60.0);
      col = mix(col, col + vec3(g)*0.15, 0.4);

      // clamp & output (alphaでスクリーン合成の“濃さ”はCanvas側のstyle.opacityで調整)
      col = clamp(col, 0.0, 1.0);
      outColor = vec4(col, 1.0);
    }`;

        const prog = createProgram(gl, vs, fs);
        gl.useProgram(prog);

        // Uniform locations
        const u = {
            time: gl.getUniformLocation(prog, 'u_time'),
            res: gl.getUniformLocation(prog, 'u_res'),
            count: gl.getUniformLocation(prog, 'u_count'),
            flickerMin: gl.getUniformLocation(prog, 'u_flickerMin'),
            flickerMax: gl.getUniformLocation(prog, 'u_flickerMax'),
            pointer: gl.getUniformLocation(prog, 'u_pointer'),
            pointerActive: gl.getUniformLocation(prog, 'u_pointerActive'),
            projA: new Array(MAX_P),
            projB: new Array(MAX_P),
        };
        for (let i = 0; i < MAX_P; i++) {
            u.projA[i] = gl.getUniformLocation(prog, `u_projA[${i}]`);
            u.projB[i] = gl.getUniformLocation(prog, `u_projB[${i}]`);
        }

        // State
        gl.bindVertexArray(vao);
        gl.disable(gl.DEPTH_TEST);
        gl.enable(gl.BLEND);
        // 通常のアルファブレンド（背景は透明）。合成はCSSの mix-blend-mode: screen に任せる。
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        _pmState.vao = vao;
        _pmState.prog = prog;
        _pmState.u = u;
    }

    function createProgram(gl, vsSrc, fsSrc) {
        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, vsSrc);
        gl.compileShader(vs);
        if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {
            console.error('[pm_webgl] VS error:', gl.getShaderInfoLog(vs));
            gl.deleteShader(vs);
            return null;
        }
        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, fsSrc);
        gl.compileShader(fs);
        if (!gl.getShaderParameter(fs, gl.COMPLETE_STATUS) && !gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
            console.error('[pm_webgl] FS error:', gl.getShaderInfoLog(fs));
            gl.deleteShader(vs);
            gl.deleteShader(fs);
            return null;
        }
        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
            console.error('[pm_webgl] Link error:', gl.getProgramInfoLog(prog));
            gl.deleteShader(vs);
            gl.deleteShader(fs);
            gl.deleteProgram(prog);
            return null;
        }
        gl.deleteShader(vs);
        gl.deleteShader(fs);
        return prog;
    }

    // =============== Loop =================
    let lastT = performance.now();
    function loop(now) {
        if (!_pmState.running) return;
        const { gl, prog, u, canvas, projectors } = _pmState;

        const dt = Math.min(0.033, (now - lastT) / 1000);
        lastT = now;

        // Update projectors (CPU)
        for (let i = 0; i < projectors.length; i++) {
            const p = projectors[i];
            p.x += p.vx * dt * 0.1;
            p.y += p.vy * dt * 0.1;
            if (p.x < 0) { p.x = 0; p.vx *= -1; }
            if (p.x > 1) { p.x = 1; p.vx *= -1; }
            if (p.y < 0) { p.y = 0; p.vy *= -1; }
            if (p.y > 1) { p.y = 1; p.vy *= -1; }
        }

        // GL draw
        gl.viewport(0, 0, _pmState.W, _pmState.H);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        gl.useProgram(prog);

        // uniforms
        gl.uniform1f(u.time, (now - _pmState.startTime) / 1000);
        gl.uniform2f(u.res, _pmState.W, _pmState.H);
        gl.uniform1i(u.count, projectors.length);
        gl.uniform1f(u.flickerMin, _pmState.flickerMin);
        gl.uniform1f(u.flickerMax, _pmState.flickerMax);

        const ptr = _pmState.pointer;
        gl.uniform2f(u.pointer, ptr.x, 1.0 - ptr.y); // GLはy上向きだが、ここではそのまま使うので変換不要でもOK
        gl.uniform1i(u.pointerActive, ptr.active ? 1 : 0);

        // pack projector uniforms
        const minWHNorm = 1.0; // 半径は既に正規化で渡す（minWH で拡大）
        for (let i = 0; i < MAX_P; i++) {
            if (i < projectors.length) {
                const p = projectors[i];
                gl.uniform4f(u.projA[i], p.x, 1.0 - p.y, p.r * minWHNorm, 0.0);
                gl.uniform4f(u.projB[i], p.hue, p.phase, p.flickerSpeed, p.flickerPhase);
            } else {
                gl.uniform4f(u.projA[i], 0, 0, 0, 0);
                gl.uniform4f(u.projB[i], 0, 0, 0, 0);
            }
        }

        gl.bindVertexArray(_pmState.vao);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        _pmState.requestId = requestAnimationFrame(loop);
    }
})();
