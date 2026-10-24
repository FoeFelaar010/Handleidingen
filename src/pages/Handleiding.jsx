import { useEffect, useRef, useState } from 'react'
import Icoon from '../components/Icoon.jsx'
import { maakCodeblokken } from '../arduino.js'

function voegKopieerknopToe(pre) {
  const box = pre.parentElement
  if (box.querySelector('.code-bar')) return
  const bar = document.createElement('div')
  bar.className = 'code-bar'
  bar.innerHTML = '<span>Code</span><button type="button" class="code-copy">📋 Kopieer code</button>'
  bar.querySelector('button').addEventListener('click', async (e) => {
    const b = e.currentTarget
    try { await navigator.clipboard.writeText(pre.textContent) } catch {
      const r = document.createRange(); r.selectNodeContents(pre)
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); document.execCommand('copy')
    }
    b.textContent = '✓ Gekopieerd!'
    setTimeout(() => { b.textContent = '📋 Kopieer code' }, 1800)
  })
  box.prepend(bar)
}

function Extra({ x }) {
  return (
    <figure className="anim">
      <iframe src={x.src} title={x.titel} loading="lazy" allow="clipboard-write" />
      <figcaption>
        Op de website kun je dit uitproberen: {x.titel} · <a className="anim-open" href={x.src} target="_blank" rel="noopener">Open in een groot venster</a>
      </figcaption>
    </figure>
  )
}

// Extra's met "na" komen onder het hoofdstuk waarvan de id dat stukje bevat; de rest in een eigen hoofdstuk "Uitproberen"
function verdeelExtras(extras = [], secties) {
  const perSectie = {}, los = []
  for (const x of extras) {
    const s = x.na && secties.find((s) => s.id.includes(x.na))
    if (s) (perSectie[s.id] ||= []).push(x)
    else los.push(x)
  }
  return { perSectie, los }
}

export default function Handleiding({ item, anker, navOpen, setNavOpen }) {
  const [data, setData] = useState(null)
  const [fout, setFout] = useState(false)
  const [actief, setActief] = useState(null)
  const mainRef = useRef(null)

  useEffect(() => {
    let weg = false
    setData(null); setFout(false)
    fetch(`data/${item.slug}.json?v=${__BOUW__}`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json() })
      .then((d) => { if (!weg) setData(d) })
      .catch(() => { if (!weg) setFout(true) })
    return () => { weg = true }
  }, [item.slug])

  useEffect(() => {
    document.title = data ? `${data.titel} · Handleidingen` : 'Handleidingen'
  }, [data])

  // na laden: naar het gekozen hoofdstuk, anders naar boven
  useEffect(() => {
    if (!data) return
    const el = anker && document.getElementById(anker)
    if (el) el.scrollIntoView()
    else if (!anker) window.scrollTo(0, 0)
  }, [data, anker])

  // Arduino-code als codeblok (oude Word-bestanden), en een kopieerknop bij elk codeblok uit stijl Code (v27)
  useEffect(() => {
    if (!data || !mainRef.current) return
    if (item.slug === 'arduino') maakCodeblokken(mainRef.current)
    mainRef.current.querySelectorAll('.code > pre').forEach(voegKopieerknopToe)
  }, [data, item.slug])

  // huidig hoofdstuk oplichten in het menu
  useEffect(() => {
    if (!data || !('IntersectionObserver' in window)) return
    const io = new IntersectionObserver((es) => {
      for (const en of es) if (en.isIntersecting) setActief(en.target.id)
    }, { rootMargin: '-15% 0px -75% 0px' })
    document.querySelectorAll('section.ch').forEach((s) => io.observe(s))
    return () => io.disconnect()
  }, [data])

  if (fout) {
    return (
      <main id="main" className="home">
        <p className="crumb"><a href="#/">Alle handleidingen</a> / {item.groep}</p>
        <h1>{item.titel}</h1>
        <p>Deze handleiding staat nog niet online. Probeer het later nog eens.</p>
      </main>
    )
  }
  if (!data) return <main id="main" className="home"><p className="laden">Handleiding laden…</p></main>

  const { perSectie, los } = verdeelExtras(item.extras, data.secties)
  const hoofdstukken = [...data.secties.map((s) => ({ id: s.id, titel: s.titel })), ...(los.length ? [{ id: 'uitproberen', titel: 'Uitproberen' }] : [])]

  return (
    <div className="layout">
      <nav id="nav" className={`nav${navOpen ? ' open' : ''}`} aria-label="Hoofdstukken">
        <a className="back" href="#/">Alle handleidingen</a>
        <p className="nav-t">{data.titel}</p>
        <ol>
          {hoofdstukken.map((h) => (
            <li key={h.id}>
              <a href={`#/${item.slug}/${h.id}`} aria-current={actief === h.id ? 'true' : undefined} onClick={() => setNavOpen(false)}>{h.titel}</a>
            </li>
          ))}
        </ol>
      </nav>
      <main id="main" ref={mainRef}>
        <div className="hero">
          <p className="crumb"><a href="#/">Alle handleidingen</a> / {item.groep}</p>
          <div className="title">
            <Icoon naam={item.icoon} maat={56} />
            <div>
              <h1>{data.titel} {item.beta && <span className="beta">Beta</span>}</h1>
              {data.sub && <p className="sub" dangerouslySetInnerHTML={{ __html: data.sub }} />}
            </div>
          </div>
          {item.beta && (
            <aside className="beta-note"><b>Beta</b>Aan deze handleiding wordt nog gewerkt. Er kan nog iets veranderen of ontbreken. Klopt er iets niet? Zeg het tegen je docent.</aside>
          )}
          <div dangerouslySetInnerHTML={{ __html: data.intro }} />
        </div>
        {data.secties.map((s) => (
          <section id={s.id} className="ch" key={s.id}>
            <h2>{s.titel}</h2>
            <div dangerouslySetInnerHTML={{ __html: s.html }} />
            {(perSectie[s.id] || []).map((x) => <Extra key={x.src} x={x} />)}
          </section>
        ))}
        {los.length > 0 && (
          <section id="uitproberen" className="ch">
            <h2>Uitproberen</h2>
            {los.map((x) => <Extra key={x.src} x={x} />)}
          </section>
        )}
        <footer className="foot">Handleidingen · Melanchthon Mavo Schiebroek · versie {data.versie}</footer>
      </main>
    </div>
  )
}
